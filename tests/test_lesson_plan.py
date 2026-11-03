import json
from pathlib import Path
import re
import tempfile
import unittest
from fastapi.testclient import TestClient
from accounts.store import Store
from accounts.lesson_plan import get_plan,start_plan
from site_server import create_site

PROMPTS=json.loads((Path(__file__).resolve().parents[1]/'prompts.json').read_text(encoding='utf-8'))


class LessonPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(self.temp.name)
        self.owner=self.store.register('alice','lesson-plan-password','Alice',background=dict(language='spanish',use_starters=True))
        self.other=self.store.register('bobby','lesson-plan-password','Bob')
    def plan(self,owner=None):return get_plan(self.store,owner or self.owner,PROMPTS)
    def finish(self,prompt_id,owner=None,outcome='insufficient_evidence',error=None,unavailable=False):
        owner=owner or self.owner
        prompt=next(p for p in PROMPTS if p['id']==prompt_id)
        identity=self.store.create_attempt(owner,prompt,b'fixture')
        result=dict(overall_status='partial',target_assessment=dict(targets=[dict(word=prompt['target_words'][0],expected_phone=prompt['target_phones'][0],status=outcome)]),stage_statuses=dict(alignment=dict(status='unavailable' if unavailable else 'available'),phoneme_scoring=dict(status='available')))
        self.store.finish(owner,identity,result=result,error=error)
        return identity
    def test_preview_has_language_order_twelve_unique_steps_and_no_saved_plan(self):
        plan=self.plan();self.assertFalse(plan['started']);self.assertEqual(plan['total'],12)
        self.assertEqual(plan['next']['lesson_id'],'ship')
        self.assertEqual(len({s['lesson_id'] for s in plan['steps']}),12)
        self.assertEqual([s['lesson_id'] for s in plan['steps'][:4]],['ship','ship_see','ship_big','ship_coming'])
        self.assertEqual({s['lesson_number'] for s in plan['steps']},{1,2,3})
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM lesson_plans').fetchone()[0],0)
    def test_start_is_idempotent_and_sequence_survives_preferences_and_restart(self):
        start_plan(self.store,self.owner,PROMPTS);initial=self.plan()
        self.store.profile(self.owner,'Alice',['TH'],background=dict(language='japanese',use_starters=True))
        start_plan(self.store,self.owner,PROMPTS)
        self.assertEqual(initial['plan_id'],self.plan()['plan_id'])
        self.assertEqual(initial['steps'],self.plan()['steps'])
        reopened=Store(self.temp.name)
        self.assertEqual(get_plan(reopened,self.owner,PROMPTS)['steps'],initial['steps'])
    def test_completed_inconclusive_attempt_advances_and_repeated_attempts_count_once(self):
        start_plan(self.store,self.owner,PROMPTS)
        self.finish('ship')
        self.assertEqual(self.plan()['practiced'],1);self.assertEqual(self.plan()['next']['lesson_id'],'ship_see')
        self.finish('ship');self.assertEqual(self.plan()['practiced'],1)
        self.finish('ship_big');self.assertEqual(self.plan()['practiced'],2)
        self.assertEqual(self.plan()['next']['lesson_id'],'ship_see')
    def test_failed_missing_analysis_and_other_accounts_do_not_advance(self):
        start_plan(self.store,self.owner,PROMPTS)
        self.finish('ship',error='Failed');self.finish('ship',unavailable=True)
        self.finish('ship',owner=self.other)
        self.assertEqual(self.plan()['practiced'],0)
        self.assertFalse(self.plan(self.other)['started'])
    def test_old_and_inflight_attempts_do_not_fill_a_new_plan(self):
        self.finish('ship')
        pending=self.store.create_attempt(self.owner,PROMPTS[0],b'fixture')
        start_plan(self.store,self.owner,PROMPTS)
        self.store.finish(self.owner,pending,dict(overall_status='complete'))
        self.assertEqual(self.plan()['practiced'],0)
    def test_deletion_removes_credit_but_another_retained_attempt_keeps_it(self):
        start_plan(self.store,self.owner,PROMPTS)
        first=self.finish('ship');second=self.finish('ship')
        self.store.delete_attempt(self.owner,second);self.assertEqual(self.plan()['practiced'],1)
        self.store.delete_attempt(self.owner,first);self.assertEqual(self.plan()['practiced'],0)
    def test_restart_applies_new_preferences_without_deleting_history(self):
        start_plan(self.store,self.owner,PROMPTS);old=self.plan()['plan_id'];self.finish('ship')
        self.store.profile(self.owner,'Alice',['TH'],background=dict(language='japanese',use_starters=True))
        start_plan(self.store,self.owner,PROMPTS,restart=True)
        self.assertNotEqual(self.plan()['plan_id'],old);self.assertEqual(self.plan()['practiced'],0)
        self.assertEqual(len(self.store.history(self.owner)),1)
    def test_finished_plan_retains_sequence_and_offers_review(self):
        start_plan(self.store,self.owner,PROMPTS);steps=self.plan()['steps']
        for step in steps:self.finish(step['lesson_id'])
        plan=self.plan();self.assertTrue(plan['complete']);self.assertIsNone(plan['next'])
        self.assertEqual(plan['practiced'],12);self.assertEqual(len(plan['review']),3)
    def test_http_recording_analysis_advances_the_saved_course(self):
        import io,time,wave
        output=io.BytesIO()
        with wave.open(output,'wb') as audio:
            audio.setparams((1,2,16000,0,'NONE','not compressed'));audio.writeframes(b'\x01\x00'*1600)
        def analyzer(*args,**kwargs):
            return dict(overall_status='partial',stage_statuses=dict(alignment=dict(status='available'),phoneme_scoring=dict(status='available')),
                target_assessment=dict(targets=[dict(expected_phone='IH',status='insufficient_evidence')]))
        app=create_site(data_root=self.temp.name,prompts=PROMPTS,analyzer=analyzer)
        with TestClient(app,base_url='http://localhost') as client:
            client.cookies.set('accent_session',self.store.new_session(self.owner))
            page=client.get('/practice');token=re.search('name="csrf-token" content="([^"]+)"',page.text).group(1)
            headers={'X-CSRF-Token':token}
            plan=client.post('/api/lesson-plan/start',headers=headers).json()
            self.assertEqual(plan['next']['lesson_id'],'ship')
            response=client.post('/api/attempts?prompt_id=ship',content=output.getvalue(),headers={**headers,'Content-Type':'audio/wav'})
            self.assertEqual(response.status_code,202)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                state=client.get('/api/attempts/'+response.json()['attempt_id']).json()
                if state['status'] not in ('queued','processing'):break
                time.sleep(.02)
            self.assertEqual(state['status'],'completed')
            plan=client.get('/api/lesson-plan').json()
            self.assertEqual(plan['practiced'],1);self.assertEqual(plan['next']['lesson_id'],'ship_see')
            self.assertEqual(plan['next']['lesson_step'],2)

    def test_http_owner_csrf_restart_confirmation_and_no_browser_mark_complete(self):
        app=create_site(data_root=self.temp.name,prompts=PROMPTS,analyzer=lambda *a,**k:None)
        with TestClient(app,base_url='http://localhost') as client:
            self.assertEqual(client.get('/api/lesson-plan').status_code,401)
            client.cookies.set('accent_session',self.store.new_session(self.owner))
            page=client.get('/practice')
            csrf=re.search('name="csrf-token" content="([^"]+)"',page.text).group(1)
            headers={'X-CSRF-Token':csrf}
            self.assertEqual(client.post('/api/lesson-plan/start').status_code,403)
            response=client.post('/api/lesson-plan/start',headers=headers,json=dict(user_id=self.other,practiced=12))
            self.assertTrue(response.json()['started']);self.assertEqual(response.json()['practiced'],0)
            self.assertFalse(self.plan(self.other)['started'])
            self.assertEqual(client.post('/api/lesson-plan/restart',headers=headers,json={}).status_code,422)
            old=response.json()['plan_id']
            response=client.post('/api/lesson-plan/restart',headers=headers,json={'restart':True})
            self.assertNotEqual(response.json()['plan_id'],old)
            self.assertIn('My lesson plan',client.get('/profile').text)


if __name__=='__main__':unittest.main()
