"""Owner-scoped coaching summaries from saved, current analysis results."""
from datetime import datetime, timezone
import json

SOUNDS={
 'TH':dict(word='think',tip='Let air flow gently with your tongue tip lightly between your teeth.'),
 'IH':dict(word='ship',tip='Use a short, relaxed vowel in ship; compare it with the longer vowel in sheep.'),
 'AE':dict(word='bad',tip='Open your jaw for the vowel in bad; compare it with bed.'),
}
LABELS={'practice':'Practice suggested','supported':'Expected sound favored','inconclusive':'Try another recording'}


def profile_progress(store,owner,prompts,*,now=None):
    now=now if now is not None else datetime.now(timezone.utc).timestamp()
    with store.connect() as db:
        user=db.execute('SELECT goals FROM users WHERE id=?',(owner,)).fetchone()
        if not user:raise LookupError('Profile not found.')
        goals=json.loads(user['goals'])
        # Never read audio blobs; ignore empty drafts and deleted records.
        rows=db.execute('''SELECT a.id,a.sentence,a.created,a.status,a.result,p.body
            FROM attempts a LEFT JOIN practice_state p ON p.attempt_id=a.id
            WHERE a.user_id=? AND a.deleted=0 AND (a.audio IS NOT NULL OR EXISTS
                (SELECT 1 FROM practice_assets x WHERE x.attempt_id=a.id AND x.role='learner'))
            ORDER BY a.created DESC,a.id DESC LIMIT 100''',(owner,)).fetchall()
    counts={phone:[] for phone in SOUNDS}
    activities=[];analyzed=0;failed=0;generation=0;days=set()
    today=int(now//86400)
    for row in rows:
        day=int(row['created']//86400)
        if 0<=today-day<7:days.add(day)
        state=json.loads(row['body']) if row['body'] else None
        result=json.loads(row['result']) if row['result'] else {}
        complete=(state['analysis_status']=='completed' if state else row['status']=='completed' and bool(result) and result.get('overall_status')!='failed')
        failure=(state['analysis_status']=='failed' if state else row['status']=='failed')
        analyzed+=int(complete);failed+=int(failure)
        generation+=int(bool(state and state.get('generation_status')=='completed'))
        outcomes={}
        if complete:
            source=state if state else result
            targets=source.get('sound_results') if state else source.get('target_assessment',{}).get('targets',[])
            for target in targets or []:
                phone=target.get('expected_phone')
                outcome=target.get('outcome') if state else {'alternative_favored':'practice','expected_supported':'supported','insufficient_evidence':'inconclusive'}.get(target.get('status'))
                if phone not in SOUNDS or outcome not in LABELS:continue
                # One observation per sound per attempt. A possible substitution
                # takes precedence over uncertainty and expected-sound support.
                priority={'practice':3,'inconclusive':2,'supported':1}
                if priority[outcome]>priority.get(outcomes.get(phone),0):outcomes[phone]=outcome
            for phone,outcome in outcomes.items():
                if len(counts[phone])<5:counts[phone].append(outcome)
        if len(activities)<5:
            activities.append(dict(attempt_id=row['id'],sentence=row['sentence'],created=row['created'],
                status='Analysis finished' if complete else 'Analysis could not finish' if failure else 'Awaiting analysis',
                sounds=[dict(phone=p,outcome=o,label=LABELS[o]) for p,o in outcomes.items()]))
    sounds=[]
    for phone,spec in SOUNDS.items():
        recent=counts[phone];latest=recent[0] if recent else None
        reason=('A recent check suggested practicing this sound.' if latest=='practice' else
                'The latest check was inconclusive. Try a clear, short recording.' if latest=='inconclusive' else
                'The latest model check favored the expected sound. Keep practicing in a new sentence.' if latest=='supported' else
                'This is one of your selected goals. Start with a short sentence.' if phone in goals else
                'No usable sound feedback yet. Try a first recording.')
        lesson=next((p for p in prompts if phone in p.get('target_phones',[])),None)
        sounds.append(dict(phone=phone,**spec,selected=phone in goals,latest=latest,label=LABELS.get(latest,'Not assessed yet'),
            observations=len(recent),practice=recent.count('practice'),supported=recent.count('supported'),
            inconclusive=recent.count('inconclusive'),reason=reason,lesson_id=lesson['id'] if lesson else None,
            sentence=lesson['text'] if lesson else None))
    ranked=sorted(sounds,key=lambda s:({'practice':0,'inconclusive':1,None:2,'supported':3}[s['latest']],not s['selected'],list(SOUNDS).index(s['phone'])))
    message=('Make your first recording to build your personal practice plan.' if not rows else
             'Your recordings are saved. Analyze one to get sound-specific feedback.' if not analyzed else
             'Your next practice is based on your latest sound checks and selected goals.')
    if failed and not analyzed:message='Some analyses could not finish. Retry a short preset lesson; saved recordings are still in History.'
    return dict(summary=message,recordings=len(rows),analyzed=analyzed,failed=failed,examples=generation,active_days_7= len(days),
        sounds=sounds,recommendations=ranked,activity=activities,
        window='Based on your latest 100 saved recordings, with up to five current analysis results per sound. Active days use UTC.',
        note='Experimental model observations, not pronunciation grades or proof of improvement. Inconclusive checks are not errors.')
