"""Real local demo rehearsal using public synthetic example audio, never user data.

Exercises actual Whisper/MFA/phoneme/Kokoro engines. Synthetic speech validates
wiring and model availability, not human pronunciation accuracy.
"""
import io
import json
from pathlib import Path
import re
import secrets
import sys
import tempfile
import time
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from site_server import create_site


def main():
    checks=[]
    timings={}
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
        print('PASS',name,flush=True)
    def headers(client,response):
        return {'X-CSRF-Token':re.search('name="csrf-token" content="([^"]+)"',response.text).group(1)}
    def signup(client,username,password):
        client.get('/signup')
        response=client.post('/signup',data=dict(csrf=client.cookies['accent_login_csrf'],username=username,password=password,display_name='Demo rehearsal'))
        check('signup_'+username,response.status_code==200)
        return headers(client,response)
    (ROOT/'runs').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='combined-demo-',dir=ROOT/'runs') as folder:
        password=secrets.token_urlsafe(24)
        with TestClient(create_site(data_root=folder),base_url='http://localhost') as client:
            auth=signup(client,'demo_rehearsal',password)
            for page in ('/practice','/profile','/history','/help','/privacy','/terms'):
                check('page_'+page,client.get(page).status_code==200)
            response=client.post('/api/profile',json=dict(display_name='Demo Learner',goals=['TH','IH','AE']),headers=auth)
            check('profile_save',response.status_code==200 and response.json()['profile']['display_name']=='Demo Learner')
            lessons=client.get('/api/lessons').json()
            check('preset_lessons',len(lessons)==12)
            for lesson in lessons:
                check('example_'+lesson['id'],client.get('/site-assets/examples/'+lesson['id']+'.wav').status_code==200)
            for mode in ('custom_text','free_speech'):
                response=client.post('/api/sessions',json=dict(input_mode=mode),headers=auth)
                check('create_'+mode,response.status_code==200)
                state=response.json()
            identity=state['attempt_id']
            response=client.post(f'/api/sessions/{identity}/recording?expected_revision={state["input_revision"]}',content=(ROOT/'web_assets/examples/think.wav').read_bytes(),headers={**auth,'Content-Type':'audio/wav'})
            check('attach_synthetic_fixture',response.status_code==200)
            def wait(kind):
                deadline=time.monotonic()+240
                while time.monotonic()<deadline:
                    response=client.get('/api/sessions/'+identity)
                    check_status=response.status_code==200
                    if not check_status:raise AssertionError('polling failed')
                    current=response.json()
                    if current[kind+'_status'] not in ('queued','processing'):
                        if current[kind+'_status']!='completed':raise AssertionError(kind+': '+str(current['errors']))
                        return current
                    time.sleep(.5)
                raise TimeoutError(kind)
            state=wait('transcription')
            check('real_whisper',bool(state['recognized_text']))
            response=client.post(f'/api/sessions/{identity}/confirm',json=dict(text='I think so.',expected_revision=state['input_revision']),headers=auth)
            check('confirm_transcript',response.status_code==200)
            state=response.json()
            for kind in ('analysis','generation','generation'):
                response=client.post(f'/api/sessions/{identity}/jobs/{kind}',json=dict(input_revision=state['input_revision']),headers=auth)
                check('queue_'+kind,response.status_code==202)
                state=wait(kind)
                check('real_'+kind,state[kind+'_status']=='completed')
                timings.setdefault(kind,[]).append(state['timings'][kind])
            check('sound_feedback_present',bool(state['sound_results']))
            progress=client.get('/api/profile/progress').json()
            check('live_profile_counts',progress['recordings']==1 and progress['analyzed']==1 and progress['examples']==1)
            check('live_sound_feedback',any(s['observations'] for s in progress['sounds']))
            response=client.get(f'/api/sessions/{identity}/audio/{state["generated_audio_id"]}')
            check('private_generated_playback',response.status_code==200)
            with wave.open(io.BytesIO(response.content),'rb') as audio:
                check('kokoro_24khz',audio.getframerate()==24000 and audio.getnframes()>0)
            check('history_contains_recording',any(row['id']==identity for row in client.get('/api/attempts').json()['attempts']))
            check('suggestions',client.get('/api/suggestions').status_code==200)
            with TestClient(client.app,base_url='http://localhost') as other:
                signup(other,'demo_other',secrets.token_urlsafe(24))
                check('other_account_denied',other.get('/api/sessions/'+identity).status_code==404)
                check('other_profile_has_no_activity',other.get('/api/profile/progress').json()['recordings']==0)
                check('other_audio_denied',other.get(f'/api/sessions/{identity}/audio/{state["generated_audio_id"]}').status_code==404)
            check('delete_attempt',client.delete('/api/attempts/'+identity,headers=auth).status_code==200)
            check('deleted_attempt_unavailable',client.get('/api/sessions/'+identity).status_code==404)
            check('deleted_activity_removed_from_profile',client.get('/api/profile/progress').json()['recordings']==0)
            check('logout',client.post('/logout',data={'csrf':auth['X-CSRF-Token']}).status_code==200)
            check('logged_out_denied',client.get('/api/me').status_code==401)
        with TestClient(create_site(data_root=folder),base_url='http://localhost') as client:
            client.get('/login')
            response=client.post('/login',data=dict(csrf=client.cookies['accent_login_csrf'],username='demo_rehearsal',password=password))
            check('signin_after_restart',response.status_code==200)
            check('profile_persisted',client.get('/api/me').json()['display_name']=='Demo Learner')
    report=dict(checks_passed=checks,timings=timings,scope='Real local speech and generation engines using synthetic fixture audio. No human accuracy claim. Temporary accounts only.')
    path=ROOT/'runs/combined_demo_smoke.json'
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=len(checks),timings=timings)),flush=True)


if __name__=='__main__':main()
