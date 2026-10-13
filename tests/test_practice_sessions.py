"""Real SQLite/login/HTTP/revision tests; controlled speech and generation doubles."""
import io
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest
import wave

from fastapi.testclient import TestClient
from site_server import create_site
from accounts.sessions import Conflict


def wav():
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x01\x00'*1600)
    return out.getvalue()


class Speech:
    def run(self,*args,operation=None,**kwargs):
        if operation['kind']=='transcription':
            return dict(status='completed',recognized_text='I think so',model_id='fixture',model_revision='fixture')
        return dict(ok=True,analysis_status='completed',sound_results=[dict(word='think',word_index=1,phone_index=0,
                    expected_phone='TH',alternative_phone=None,outcome='inconclusive',reason_code='INSUFFICIENT_EVIDENCE',message='Uncertain')],limitations=[])


def generator(text,accent,*,output_dir):
    asset='synthetic-'+'b'*32
    path=output_dir/(asset+'.wav');path.write_bytes(wav()+b'generated')
    return dict(ok=True,generated_audio_id=asset)


class PracticeSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=create_site(data_root=self.tmp.name,speech=Speech(),generator=generator)
        self.client=self.enterContext(TestClient(self.app,base_url='http://localhost'))
        self.headers=self.signup(self.client,'alice')
        self.store=self.app.state.store

    def signup(self,client,name):
        client.get('/signup')
        r=client.post('/signup',data=dict(csrf=client.cookies['accent_login_csrf'],username=name,password='test-password-123',display_name=name))
        self.assertEqual(r.status_code,200)
        return {'X-CSRF-Token':re.search('name="csrf-token" content="([^"]+)"',r.text).group(1)}

    def create(self):
        r=self.client.post('/api/sessions',json={'input_mode':'free_speech','user_id':'fake'},headers=self.headers)
        self.assertEqual(r.status_code,200,r.text)
        self.state=r.json();self.id=self.state['attempt_id']
        r=self.client.post(f'/api/sessions/{self.id}/recording?expected_revision=1',content=wav(),headers={**self.headers,'Content-Type':'audio/wav'})
        self.assertEqual(r.status_code,200,r.text)
        return self.wait('transcription')

    def wait(self,kind):
        for _ in range(150):
            r=self.client.get('/api/sessions/'+self.id)
            self.assertEqual(r.status_code,200,r.text)
            self.state=r.json()
            if self.state[kind+'_status'] not in {'queued','processing'}: return self.state
            time.sleep(.01)
        self.fail('Job did not finish')

    def confirm(self,text='I think so'):
        r=self.client.post(f'/api/sessions/{self.id}/confirm',json=dict(text=text,expected_revision=self.state['input_revision']),headers=self.headers)
        self.assertEqual(r.status_code,200,r.text);self.state=r.json();return self.state

    def test_complete_flat_flow_private_playback_and_history(self):
        self.create()
        self.assertEqual(self.state['recognized_text'],'I think so')
        self.assertIsNone(self.state['confirmed_text'])
        self.assertNotEqual(self.state['user_id'],'fake')
        self.confirm()
        for kind in ('analysis','generation'):
            r=self.client.post(f'/api/sessions/{self.id}/jobs/{kind}',json={'input_revision':self.state['input_revision']},headers=self.headers)
            self.assertEqual(r.status_code,202,r.text);self.wait(kind)
            self.assertEqual(self.state[kind+'_status'],'completed',self.state)
        self.assertEqual(self.state['sound_results'][0]['outcome'],'inconclusive')
        for key in ('recognized_text','confirmed_text','learner_audio_id','generated_audio_id','generated_audio_type','timings','analysis_status','input_revision'):
            self.assertIn(key,self.state)
        self.assertFalse(any(k.startswith('_') for k in self.state))
        for asset in (self.state['learner_audio_id'],self.state['generated_audio_id']):
            self.assertEqual(self.client.get(f'/api/sessions/{self.id}/audio/{asset}').status_code,200)
        self.assertIn(self.id,[a['id'] for a in self.client.get('/api/attempts').json()['attempts']])

    def test_second_user_cannot_read_edit_submit_play_or_delete(self):
        self.create();self.confirm()
        bob=self.enterContext(TestClient(self.app,base_url='http://localhost'))
        headers=self.signup(bob,'bob')
        self.assertEqual(bob.get('/api/sessions/'+self.id).status_code,404)
        self.assertEqual(bob.get(f'/api/sessions/{self.id}/audio/{self.state["learner_audio_id"]}').status_code,404)
        self.assertEqual(bob.post(f'/api/sessions/{self.id}/confirm',json={'text':'I think so','expected_revision':3},headers=headers).status_code,404)
        self.assertEqual(bob.post(f'/api/sessions/{self.id}/jobs/analysis',json={'input_revision':3},headers=headers).status_code,404)
        self.assertEqual(bob.delete('/api/attempts/'+self.id,headers=headers).status_code,404)

    def test_limits_confirmation_and_csrf(self):
        self.create()
        self.assertEqual(self.client.post(f'/api/sessions/{self.id}/jobs/analysis',json={'input_revision':self.state['input_revision']},headers=self.headers).status_code,422)
        for text in ('','I '*13,'a'*201,'zzunknownword'):
            r=self.client.post(f'/api/sessions/{self.id}/confirm',json=dict(text=text,expected_revision=self.state['input_revision']),headers=self.headers)
            self.assertEqual(r.status_code,422,text)
        self.assertEqual(self.client.post('/api/sessions',json={'input_mode':'free_speech'}).status_code,403)

    def test_text_edit_rejects_stale_analysis_and_clears_generation(self):
        self.create();self.confirm()
        token=self.client.cookies['accent_session'];rev=self.state['input_revision']
        receipt=self.store.begin_practice_job(token,self.id,rev,'analysis')
        snapshot=self.store.job_snapshot(token,self.id,receipt['job_id'],rev,'analysis')
        self.confirm('I think I think so')
        self.assertFalse(self.store.publish_job(token,snapshot,'analysis',dict(ok=True,sound_results=[])))
        self.assertEqual(self.state['recognized_text'],'I think so')
        self.assertEqual(self.state['sound_results'],[])
        self.assertIsNone(self.state['generated_audio_id'])

    def test_deleted_attempt_cannot_publish(self):
        self.create();self.confirm();token=self.client.cookies['accent_session'];rev=self.state['input_revision']
        receipt=self.store.begin_practice_job(token,self.id,rev,'analysis')
        snapshot=self.store.job_snapshot(token,self.id,receipt['job_id'],rev,'analysis')
        self.client.delete('/api/attempts/'+self.id,headers=self.headers)
        self.assertFalse(self.store.publish_job(token,snapshot,'analysis',dict(ok=True,sound_results=[])))
        self.assertEqual(self.client.get('/api/sessions/'+self.id).status_code,404)

    def test_restart_keeps_confirmed_session_and_recovers_pending_job(self):
        self.create();self.confirm();token=self.client.cookies['accent_session']
        self.store.begin_practice_job(token,self.id,self.state['input_revision'],'analysis')
        from accounts.store import Store
        restarted=Store(self.tmp.name);restarted.recover_interrupted()
        state=restarted.get_session(token,self.id)
        self.assertEqual(state['analysis_status'],'failed')
        self.assertEqual(state['confirmed_text'],'I think so')
        self.assertEqual(restarted.session_asset(token,self.id,state['learner_audio_id']),wav())

    def test_registered_generated_wave_cannot_be_attached_as_learner(self):
        self.create();self.confirm()
        self.client.post(f'/api/sessions/{self.id}/jobs/generation',json={'input_revision':self.state['input_revision']},headers=self.headers)
        self.wait('generation')
        data=self.client.get(f'/api/sessions/{self.id}/audio/{self.state["generated_audio_id"]}').content
        r=self.client.post(f'/api/sessions/{self.id}/recording?expected_revision={self.state["input_revision"]}',content=data,headers={**self.headers,'Content-Type':'audio/wav'})
        self.assertEqual(r.status_code,422,r.text)

    def test_logout_cancels_pending_job_and_blocks_late_publication(self):
        self.create();self.confirm();token=self.client.cookies['accent_session'];rev=self.state['input_revision']
        receipt=self.store.begin_practice_job(token,self.id,rev,'analysis')
        snapshot=self.store.job_snapshot(token,self.id,receipt['job_id'],rev,'analysis')
        self.store.logout(token)
        self.assertFalse(self.store.publish_job(token,snapshot,'analysis',dict(ok=True,sound_results=[])))
        owner=self.store.login('alice','test-password-123');new_token=self.store.new_session(owner)
        self.assertEqual(self.store.get_session(new_token,self.id)['analysis_status'],'cancelled')

    def test_duplicate_submission_uses_existing_job_and_busy_is_explicit(self):
        self.create();self.confirm();token=self.client.cookies['accent_session'];rev=self.state['input_revision']
        first=self.store.begin_practice_job(token,self.id,rev,'analysis')
        second=self.store.begin_practice_job(token,self.id,rev,'analysis')
        self.assertEqual(first['job_id'],second['job_id'])
        jobs=self.app.state.practice_jobs
        acquired=0
        try:
            while jobs.slots.acquire(blocking=False):acquired+=1
            duplicate=self.client.post(f'/api/sessions/{self.id}/jobs/analysis',json={'input_revision':rev},headers=self.headers)
            self.assertEqual(duplicate.json()['job_id'],first['job_id'])
            r=self.client.post(f'/api/sessions/{self.id}/jobs/generation',json={'input_revision':rev},headers=self.headers)
            self.assertEqual(r.status_code,503)
            self.assertEqual(r.json()['error']['code'],'BUSY')
        finally:
            for _ in range(acquired):jobs.slots.release()

    def test_profile_suggestions_use_practice_but_not_inconclusive(self):
        self.create();self.confirm();token=self.client.cookies['accent_session'];rev=self.state['input_revision']
        for outcome,expected in [('inconclusive',[]),('practice',['TH'])]:
            receipt=self.store.begin_practice_job(token,self.id,rev,'analysis')
            snapshot=self.store.job_snapshot(token,self.id,receipt['job_id'],rev,'analysis')
            self.store.publish_job(token,snapshot,'analysis',dict(ok=True,sound_results=[dict(expected_phone='TH',outcome=outcome)]))
            self.assertEqual(self.client.get('/api/suggestions').json()['phones'],expected)


if __name__=='__main__': unittest.main()
