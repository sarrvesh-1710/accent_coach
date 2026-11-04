"""Stable, owner-scoped sentence plans and analysis-derived practice progress."""
import json
import time
import uuid

from accounts.coaching import profile_progress,SOUNDS

SENTENCES={
 'TH':['think','think_can','think_again','think_fine'],
 'IH':['ship','ship_see','ship_big','ship_coming'],
 'AE':['bad_bed','bad_day','bad_plan','bad_idea'],
}


def preview_plan(store,owner,prompts):
    feedback=profile_progress(store,owner,prompts)
    steps=[];seen=set()
    for recommendation in feedback['recommendations']:
        phone=recommendation['phone']
        candidates=[p for p in prompts if phone in p.get('target_phones',[]) or p['id'] in SENTENCES[phone]]
        candidates.sort(key=lambda p:SENTENCES[phone].index(p['id']) if p['id'] in SENTENCES[phone] else len(SENTENCES[phone]))
        for prompt in candidates:
            if prompt['id'] in seen:continue
            seen.add(prompt['id'])
            steps.append(dict(lesson_id=prompt['id'],sentence=prompt['text'],phone=phone,tip=prompt.get('practice_tip',SOUNDS[phone]['tip'])))
    # Keep any newly configured non-target lessons accessible in the plan too.
    for prompt in prompts:
        if prompt['id'] not in seen:
            steps.append(dict(lesson_id=prompt['id'],sentence=prompt['text'],phone=None,tip=prompt.get('practice_tip','')))
    return dict(version=1,plan_id=None,started_at=None,steps=steps,
        based_on='Your personal sound feedback and goals' if not feedback['starter']['active'] else feedback['starter']['label']+' and selected goals')


def start_plan(store,owner,prompts,*,restart=False):
    draft=preview_plan(store,owner,prompts)
    if not draft['steps']:raise ValueError('No practice sentences are configured yet.')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        previous=db.execute('SELECT body FROM lesson_plans WHERE user_id=?',(owner,)).fetchone()
        if previous and not restart:return
        draft.update(plan_id=uuid.uuid4().hex,started_at=time.time())
        db.execute('INSERT INTO lesson_plans VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body',(owner,json.dumps(draft)))
        db.execute('DELETE FROM lesson_plan_steps WHERE user_id=?',(owner,))


def completed_analysis(result):
    """Practice completion includes uncertain sound evidence, never failed processing."""
    if not isinstance(result,dict) or result.get('overall_status') not in ('complete','partial','completed'):return False
    stages=result.get('stage_statuses') or {}
    for name in ('learner_dsp','alignment','phoneme_scoring'):
        usable={'ok','available','warning','partial'}
        if name=='phoneme_scoring':usable.add('uncertain')
        if name in stages and stages[name].get('status') not in usable:return False
    return True


def record_completion(db,owner,identity,result):
    """Called inside the immutable attempt publication transaction, never by UI."""
    if not completed_analysis(result):return
    row=db.execute('SELECT body FROM lesson_plans WHERE user_id=?',(owner,)).fetchone()
    if not row:return
    plan=json.loads(row['body'])
    attempt=db.execute('SELECT prompt_id,sentence,created,status FROM attempts WHERE id=? AND user_id=? AND deleted=0',(identity,owner)).fetchone()
    if not attempt or attempt['status']!='completed' or attempt['created']<plan['started_at']:return
    if not any(s['lesson_id']==attempt['prompt_id'] and s['sentence']==attempt['sentence'] for s in plan['steps']):return
    db.execute('INSERT OR IGNORE INTO lesson_plan_steps VALUES (?,?,?,?)',(owner,plan['plan_id'],attempt['prompt_id'],identity))


def get_plan(store,owner,prompts):
    with store.connect() as db:
        row=db.execute('SELECT body FROM lesson_plans WHERE user_id=?',(owner,)).fetchone()
        plan=json.loads(row['body']) if row else None
        completed=set()
        if plan:
            completed={r['prompt_id'] for r in db.execute('''SELECT DISTINCT p.prompt_id FROM lesson_plan_steps p
                JOIN attempts a ON a.id=p.attempt_id AND a.user_id=p.user_id
                WHERE p.user_id=? AND p.plan_id=? AND a.deleted=0 AND a.status='completed' ''',(owner,plan['plan_id']))}
            # Reconcile previously finished uncertain analyses that older versions omitted.
            # Derive credit without rewriting recordings or counting pre-plan history.
            candidates=db.execute("SELECT prompt_id,sentence,result FROM attempts WHERE user_id=? AND deleted=0 AND status='completed' AND created>=?",(owner,plan['started_at'])).fetchall()
            planned={(s['lesson_id'],s['sentence']) for s in plan['steps']}
            for attempt in candidates:
                if (attempt['prompt_id'],attempt['sentence']) not in planned:continue
                try:result=json.loads(attempt['result'] or 'null')
                except (ValueError,TypeError):continue
                if completed_analysis(result):completed.add(attempt['prompt_id'])
    if not plan:plan=preview_plan(store,owner,prompts)
    catalog={p['id']:p for p in prompts}
    steps=[];groups={}
    for position,step in enumerate(plan['steps'],1):
        phone=step['phone']
        if phone not in groups:groups[phone]=len(groups)+1
        available=step['lesson_id'] in catalog and catalog[step['lesson_id']]['text']==step['sentence']
        steps.append(dict(step,number=position,lesson_number=groups[phone],available=available,practiced=available and step['lesson_id'] in completed))
    for step in steps:
        group_steps=[s for s in steps if s['lesson_number']==step['lesson_number']]
        step['lesson_step']=group_steps.index(step)+1
        step['lesson_total']=len(group_steps)
    usable=[s for s in steps if s['available']]
    next_step=next((s for s in usable if not s['practiced']),None)
    review=[]
    if plan['plan_id'] and not next_step and usable:
        for sound in profile_progress(store,owner,prompts)['recommendations']:
            if sound['latest'] in ('practice','inconclusive') and sound['lesson_id']:
                review.append(dict(phone=sound['phone'],sentence=sound['sentence'],lesson_id=sound['lesson_id'],reason=sound['reason']))
    return dict(plan_id=plan['plan_id'],started=bool(plan['plan_id']),started_at=plan['started_at'],based_on=plan['based_on'],
        total=len(usable),lessons_total=len(groups),practiced=sum(s['practiced'] for s in usable),next=next_step,steps=steps,
        complete=bool(plan['plan_id'] and usable and not next_step),review=review,catalog_changed=len(usable)!=len(steps),
        explanation='Follow the sentences in order. A saved recording with completed analysis marks a sentence as practiced, even when feedback is inconclusive. This is practice progress, not a grade. Failed processing does not advance the plan.')
