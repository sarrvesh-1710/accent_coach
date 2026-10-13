"""Bounded jobs joining authenticated SQLite snapshots with isolated engines."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import time
import re
import json

from accounts.sessions import Conflict, Busy


class PracticeJobs:
    def __init__(self, store, speech=None, generator=None, *, pool=None, slots=None):
        if speech is None:
            from analysis_service import SERVICE
            speech=SERVICE
        if generator is None:
            from voice_generation.generator import generate_audio
            generator=generate_audio
        self.store,self.speech,self.generator=store,speech,generator
        self.owns_pool=pool is None
        self.pool=pool or ThreadPoolExecutor(max_workers=1,thread_name_prefix='confirmed-practice')
        self.slots=slots or threading.BoundedSemaphore(8)

    def submit(self, token, identity, revision, kind):
        existing=self.store.active_job_receipt(token,identity,revision,kind)
        if existing:return existing
        if not self.slots.acquire(blocking=False):
            raise Busy('The practice queue is full. Please try again shortly.')
        try:
            receipt=self.store.begin_practice_job(token,identity,revision,kind)
            if receipt.pop('_already_active',False):
                self.slots.release()
                return receipt
            self.pool.submit(self.run,token,receipt,kind)
            return receipt
        except Exception:
            self.slots.release()
            raise

    def run(self,token,receipt,kind):
        snapshot=None
        try:
            snapshot=self.store.job_snapshot(token,receipt['attempt_id'],receipt['job_id'],receipt['input_revision'],kind)
            began=time.monotonic()
            work=self.store.root/'work';work.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='confirmed-',dir=work) as folder:
                path=Path(folder)/'learner.wav';path.write_bytes(snapshot.pop('_recording'))
                if kind=='transcription':
                    result=self.speech.run(None,None,operation=dict(kind=kind,path=str(path)))
                    result['learner_audio_id']=snapshot['learner_audio_id']
                elif kind=='analysis':
                    snapshot['learner_audio_path']=str(path)
                    result=self.speech.run(None,None,operation=dict(kind=kind,snapshot=snapshot))
                else:
                    result=self.generator(snapshot['confirmed_text'],snapshot['target_accent'],output_dir=Path(folder))
                stages=result.get('timings',{}).get(kind,{}).get('stages_ms',{})
                result['timings']={kind:dict(queue_ms=(began-snapshot['_queued'])*1000,
                    processing_ms=(time.monotonic()-began)*1000,
                    **({'stages_ms':stages} if kind=='analysis' else {}))}
                generated=None
                if kind=='generation' and result.get('ok'):
                    asset_id=result.get('generated_audio_id','')
                    if not re.fullmatch(r'synthetic-[0-9a-f]{32}',asset_id):
                        raise ValueError('Invalid generated asset identity')
                    output=Path(folder)/(asset_id+'.wav')
                    if not output.resolve().is_relative_to(Path(folder).resolve()):
                        raise ValueError('Invalid generated asset location')
                    generated=output.read_bytes()
                self.store.publish_job(token,snapshot,kind,result,generated=generated)
        except (PermissionError,Conflict):
            pass
        except Exception as exc:
            if snapshot:
                result=dict(ok=False,error=dict(code='TIMEOUT' if isinstance(exc,TimeoutError) else 'MODEL_UNAVAILABLE',
                            user_message='Processing could not finish. Please retry.',retryable=True))
                self.store.publish_job(token,snapshot,kind,result)
        finally:
            self.slots.release()

    def close(self):
        if self.owns_pool: self.pool.shutdown(wait=True)

    # Approved Python boundary; auth is an opaque login token, checked by Store.
    def create_attempt(self,auth,*,input_mode,target_accent,lesson_id=None):
        return self.store.create_session(auth,input_mode=input_mode,target_accent=target_accent,lesson_id=lesson_id)

    def get_attempt(self,auth,attempt_id):return self.store.get_session(auth,attempt_id)
    def list_attempts(self,auth,*,limit=50,cursor=None):return self.store.list_sessions(auth,limit=limit,cursor=cursor)
    def delete_attempt(self,auth,attempt_id):return self.store.delete_session(auth,attempt_id)
    def attach_recording(self,auth,attempt_id,upload,*,expected_revision):
        return self.store.attach_session_recording(auth,attempt_id,upload,expected_revision=expected_revision)
    def confirm_transcript(self,auth,attempt_id,text,*,expected_revision):
        return self.store.confirm_session_transcript(auth,attempt_id,text,expected_revision=expected_revision)
    def submit_transcription(self,auth,attempt_id,*,input_revision):return self.submit(auth,attempt_id,input_revision,'transcription')
    def submit_analysis(self,auth,attempt_id,*,input_revision):return self.submit(auth,attempt_id,input_revision,'analysis')
    def submit_generation(self,auth,attempt_id,*,input_revision,kind='synthetic_example'):
        if kind!='synthetic_example':raise ValueError('Voice-preserving conversion is not available.')
        return self.submit(auth,attempt_id,input_revision,'generation')
    def get_practice_suggestions(self,auth):
        with self.store.connect() as db:
            owner=self.store._auth(db,auth)
            goals=json.loads(db.execute('SELECT goals FROM users WHERE id=?',(owner,)).fetchone()['goals'])
        return dict(phones=self.store.suggestions(owner,goals))
