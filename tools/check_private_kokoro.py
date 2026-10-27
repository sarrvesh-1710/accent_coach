"""Real Kokoro + HTTP/login/SQLite checks; speech stages are controlled fixtures.

No learner recording, real account, or production database is used. This proves
generation integration and access boundaries, not recognition/assessment accuracy.
"""
import io
import json
import math
from pathlib import Path
import re
import secrets
import struct
import sys
import tempfile
import time
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from fastapi.testclient import TestClient
from site_server import create_site
from voice_generation.bridge import IsolatedKokoro


class FixtureSpeech:
    def run(self,*args,operation=None,**kwargs):
        if operation['kind']=='transcription':
            return dict(status='completed',recognized_text='I think so',model_id='controlled-fixture',model_revision='fixture')
        return dict(ok=True,analysis_status='completed',sound_results=[dict(word='think',word_index=1,
            phone_index=0,expected_phone='TH',alternative_phone=None,outcome='inconclusive',
            reason_code='INSUFFICIENT_EVIDENCE',message='Controlled fixture; no pronunciation assessment performed.')],limitations=['Speech stages are test doubles in this check.'])


def recording():
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as out:
        out.setparams((1,2,16000,0,'NONE','not compressed'))
        out.writeframes(b''.join(struct.pack('<h',int(3000*math.sin(2*math.pi*180*i/16000))) for i in range(16000)))
    return buffer.getvalue()


def main():
    results=[]
    timings=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        results.append(name);print('PASS',name,flush=True)
    (ROOT/'runs').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='private-kokoro-',dir=ROOT/'runs') as folder:
        app=create_site(data_root=folder,speech=FixtureSpeech())
        generator=app.state.practice_jobs.generator
        check('default_is_isolated_kokoro',isinstance(generator,IsolatedKokoro))
        with TestClient(app,base_url='http://localhost') as client:
            def signup(client,name):
                client.get('/signup')
                response=client.post('/signup',data=dict(csrf=client.cookies['accent_login_csrf'],
                    username=name,password=secrets.token_urlsafe(24),display_name='Kokoro integration test'))
                check('signup_'+name,response.status_code==200)
                return {'X-CSRF-Token':re.search('name="csrf-token" content="([^"]+)"',response.text).group(1)}
            headers=signup(client,'kokoro_test_a')
            response=client.post('/api/sessions',json={'input_mode':'free_speech'},headers=headers)
            check('create_private_session',response.status_code==200)
            state=response.json();identity=state['attempt_id']
            response=client.post(f'/api/sessions/{identity}/recording?expected_revision={state["input_revision"]}',
                content=recording(),headers={**headers,'Content-Type':'audio/wav'})
            check('attach_controlled_audio',response.status_code==200)
            def wait(kind):
                deadline=time.monotonic()+130
                while time.monotonic()<deadline:
                    response=client.get('/api/sessions/'+identity)
                    check_ok=response.status_code==200
                    if not check_ok:raise AssertionError('session polling unavailable')
                    state=response.json()
                    if state[kind+'_status'] not in ('queued','processing'):return state
                    time.sleep(.25)
                raise TimeoutError(kind+' did not finish')
            state=wait('transcription')
            check('fixture_transcription_finished',state['transcription_status']=='completed')
            response=client.post(f'/api/sessions/{identity}/confirm',json={'text':'I think so.','expected_revision':state['input_revision']},headers=headers)
            check('confirm_text',response.status_code==200)
            state=response.json()
            response=client.post(f'/api/sessions/{identity}/jobs/analysis',json={'input_revision':state['input_revision']},headers=headers)
            check('queue_fixture_analysis',response.status_code==202)
            state=wait('analysis');check('fixture_analysis_finished',state['analysis_status']=='completed')
            findings=state['sound_results']
            for repeat in range(2):
                response=client.post(f'/api/sessions/{identity}/jobs/generation',json={'input_revision':state['input_revision']},headers=headers)
                check('queued_generation_'+str(repeat),response.status_code==202)
                state=wait('generation')
                check('real_kokoro_completed_'+str(repeat),state['generation_status']=='completed')
                check('synthetic_role_'+str(repeat),state['generated_audio_type']=='synthetic_example' and state['generated_audio_id']!=state['learner_audio_id'])
                response=client.get(f'/api/sessions/{identity}/audio/{state["generated_audio_id"]}')
                check('authorized_playback_'+str(repeat),response.status_code==200)
                with wave.open(io.BytesIO(response.content),'rb') as audio:
                    check('valid_24khz_wav_'+str(repeat),audio.getframerate()==24000 and audio.getnframes()>0)
                stages=state['timings']['generation']['stages_ms']
                check('cold_then_warm_'+str(repeat),stages['model_load']>0 if repeat==0 else stages['model_load']==0)
                timings.append(state['timings']['generation'])
                check('analysis_preserved_'+str(repeat),state['sound_results']==findings and state['analysis_status']=='completed')
            other=TestClient(app,base_url='http://localhost')
            try:
                signup(other,'kokoro_test_b')
                check('other_account_denied',other.get('/api/sessions/'+identity).status_code==404)
                check('other_account_playback_denied',other.get(f'/api/sessions/{identity}/audio/{state["generated_audio_id"]}').status_code==404)
            finally:
                other.close()
            generator.close()
            original_python=generator.python
            generator.python=Path(folder)/'missing-python.exe'
            response=client.post(f'/api/sessions/{identity}/jobs/generation',json={'input_revision':state['input_revision']},headers=headers)
            check('queue_missing_runtime_case',response.status_code==202)
            state=wait('generation')
            check('missing_runtime_is_failure',state['generation_status']=='failed' and state['errors']['generation']['code']=='MODEL_UNAVAILABLE')
            check('failure_preserves_analysis',state['analysis_status']=='completed' and state['sound_results']==findings)
            generator.python=original_python
            check('temporary_outputs_cleaned',not list((Path(folder)/'work').rglob('*.wav')))
    report={'checks_passed':results,'generation_timings':timings,
            'scope':'Real isolated Kokoro, login/HTTP/SQLite/private playback. Transcription and assessment are controlled fixtures, not real speech/model accuracy validation.'}
    (ROOT/'runs/kokoro_private_integration_smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'checks_passed':len(results),'timings':timings}),flush=True)


if __name__=='__main__':main()
