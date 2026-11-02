import json
from pathlib import Path
import tempfile
import time
import unittest
from fastapi.testclient import TestClient
from accounts.store import Store
from accounts.coaching import profile_progress
from site_server import create_site

PROMPTS=[dict(id='think',text='I think so',target_phones=['TH']),dict(id='ship',text='The ship is here',target_phones=['IH']),dict(id='bad_bed',text='That is a bad bed',target_phones=['AE'])]


class CoachingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(self.temp.name)
        self.owner=self.store.register('alice','test-password-403','Alice')
        self.other=self.store.register('bobby','test-password-403','Bob')
    def attempt(self,phone='TH',status='alternative_favored',owner=None,created=None):
        owner=owner or self.owner
        identity=self.store.create_attempt(owner,PROMPTS[0],b'fixture')
        self.store.finish(owner,identity,dict(overall_status='completed',target_assessment=dict(targets=[dict(expected_phone=phone,status=status)])))
        if created is not None:
            with self.store.connect() as db:db.execute('UPDATE attempts SET created=? WHERE id=?',(created,identity))
        return identity
    def plan(self):return profile_progress(self.store,self.owner,PROMPTS)
    def test_empty_profile_uses_selected_goals(self):
        self.store.profile(self.owner,'Alice',['IH'])
        data=self.plan()
        self.assertEqual(data['recordings'],0)
        self.assertEqual(data['recommendations'][0]['phone'],'IH')
        self.assertEqual(data['recommendations'][0]['observations'],0)
    def test_feedback_prioritizes_practice_and_preserves_uncertainty(self):
        self.attempt('TH','alternative_favored');self.attempt('IH','insufficient_evidence');self.attempt('AE','expected_supported')
        data=self.plan();self.assertEqual(data['analyzed'],3)
        self.assertEqual(data['recommendations'][0]['phone'],'TH')
        self.assertEqual(data['sounds'][1]['inconclusive'],1)
        self.assertEqual(data['sounds'][1]['practice'],0)
        self.assertEqual(data['sounds'][2]['supported'],1)
    def test_other_accounts_and_deleted_attempts_are_excluded(self):
        self.attempt(owner=self.other)
        identity=self.attempt();self.store.delete_attempt(self.owner,identity)
        self.assertEqual(self.plan()['recordings'],0)
        self.assertEqual(self.plan()['sounds'][0]['observations'],0)
    def test_current_revision_wins_over_stale_result(self):
        token=self.store.new_session(self.owner)
        state=self.store.create_session(token,input_mode='free_speech',target_accent='en-US-general-american')
        with self.store.connect() as db:
            db.execute('INSERT INTO practice_assets VALUES (?,?,?,?,?)',('learner-test',state['attempt_id'],'learner',1,b'fixture'))
            state.update(learner_audio_id='learner-test',analysis_status='completed',sound_results=[dict(expected_phone='IH',outcome='practice')])
            self.store._save_practice(db,state)
        self.assertEqual(self.plan()['recommendations'][0]['phone'],'IH')
        with self.store.connect() as db:
            state.update(input_revision=2,analysis_status=None,sound_results=[])
            self.store._save_practice(db,state)
        self.assertEqual(self.plan()['analyzed'],0)
        self.assertTrue(all(s['observations']==0 for s in self.plan()['sounds']))
    def test_latest_result_overrides_old_advice_and_failed_does_not_grade(self):
        self.attempt(created=time.time()-86400)
        self.attempt(status='expected_supported')
        failed=self.store.create_attempt(self.owner,PROMPTS[0],b'fixture')
        self.store.finish(self.owner,failed,error='Alignment unavailable')
        data=self.plan();self.assertEqual(data['sounds'][0]['latest'],'supported')
        self.assertEqual(data['failed'],1);self.assertEqual(data['sounds'][0]['observations'],2)
    def test_sound_occurrences_are_counted_once_per_attempt(self):
        identity=self.store.create_attempt(self.owner,PROMPTS[0],b'fixture')
        self.store.finish(self.owner,identity,dict(overall_status='completed',target_assessment=dict(targets=[dict(expected_phone='TH',status='expected_supported'),dict(expected_phone='TH',status='alternative_favored')])))
        sound=self.plan()['sounds'][0]
        self.assertEqual(sound['observations'],1)
        self.assertEqual(sound['practice'],1)
    def test_summary_api_requires_auth_and_ignores_requested_owner(self):
        self.attempt(owner=self.other)
        app=create_site(data_root=self.temp.name,prompts=PROMPTS,analyzer=lambda *a,**k:None)
        with TestClient(app,base_url='http://localhost') as client:
            self.assertEqual(client.get('/api/profile/progress').status_code,401)
            client.cookies.set('accent_session',self.store.new_session(self.owner))
            response=client.get('/api/profile/progress?owner='+self.other)
            self.assertEqual(response.status_code,200);self.assertEqual(response.json()['recordings'],0)
            self.assertNotIn('password',response.text);self.assertNotIn(str(self.store.db),response.text)
            self.assertIn('My practice progress',client.get('/profile').text)
            self.assertEqual(len(response.json()['recommendations']),3)
            self.assertEqual(client.get('/api/suggestions').json(),{'phones':[]})


if __name__=='__main__':unittest.main()
