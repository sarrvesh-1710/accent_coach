"""Real SQLite/auth/HTTP/speech/TTS smoke with existing local demo audio.

Text edits containing repeats/contractions deliberately disagree with that
recording: they test diagnostic abstention, not correctly uttered speech.
"""
import json
from pathlib import Path
import re
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from site_server import create_site


def main():
    rows=[];dest=ROOT/'runs/private-free-speech-smoke.json'
    def save(name,passed,**values):
        row=dict(name=name,passed=passed,**values);rows.append(row)
        dest.write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
        if not passed:raise RuntimeError(name+' failed')
    with tempfile.TemporaryDirectory(prefix='accent_private_smoke_') as root:
        site=create_site(data_root=root)
        with TestClient(site,base_url='http://localhost') as client:
            client.get('/signup')
            response=client.post('/signup',data=dict(csrf=client.cookies['accent_login_csrf'],username='smoketester',password='smoke-test-password-403',display_name='Local smoke test'))
            headers={'X-CSRF-Token':re.search('name="csrf-token" content="([^"]+)"',response.text).group(1)}
            created=client.post('/api/sessions',json={'input_mode':'custom_text'},headers=headers).json()
            identity=created['attempt_id']
            attached=client.post(f'/api/sessions/{identity}/recording?expected_revision=1',content=(ROOT/'data/references/think.wav').read_bytes(),headers={**headers,'Content-Type':'audio/wav'})
            save('recording_attached',attached.status_code==200)
            def wait(kind):
                deadline=time.monotonic()+240
                while time.monotonic()<deadline:
                    state=client.get('/api/sessions/'+identity).json()
                    if state[kind+'_status'] not in {'queued','processing'}:return state
                    time.sleep(.25)
                raise TimeoutError(kind)
            state=wait('transcription');save('real_transcription',state['transcription_status']=='completed',has_recognized_text=bool(state['recognized_text']))
            for sentence in ('I think so','I think I think so',"I don't think so"):
                response=client.post(f'/api/sessions/{identity}/confirm',json=dict(text=sentence,expected_revision=state['input_revision']),headers=headers)
                save('confirm_'+sentence,response.status_code==200)
                state=response.json()
                receipt=client.post(f'/api/sessions/{identity}/jobs/analysis',json=dict(input_revision=state['input_revision']),headers=headers)
                save('analysis_queued_'+sentence,receipt.status_code==202)
                state=wait('analysis')
                save('analysis_completed_'+sentence,state['analysis_status']=='completed',outcomes=[r['outcome'] for r in state['sound_results']],limitations=state['limitations'],timings=state['timings'].get('analysis'))
                if sentence!='I think so':save('corrected_content_abstained_'+sentence,all(r['outcome']=='inconclusive' for r in state['sound_results']))
            receipt=client.post(f'/api/sessions/{identity}/jobs/generation',json=dict(input_revision=state['input_revision']),headers=headers)
            save('generation_queued',receipt.status_code==202)
            state=wait('generation');save('real_generation',state['generation_status']=='completed',timings=state['timings'].get('generation'),errors=state['errors'])
            played=client.get(f'/api/sessions/{identity}/audio/{state["generated_audio_id"]}')
            save('generated_playback',played.status_code==200 and played.content[:4]==b'RIFF')
            wrong=client.post(f'/api/sessions/{identity}/recording?expected_revision={state["input_revision"]}',content=played.content,headers={**headers,'Content-Type':'audio/wav'})
            save('generated_reupload_rejected',wrong.status_code==422)
    return 0


if __name__=='__main__':raise SystemExit(main())
