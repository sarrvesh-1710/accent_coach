"""Revision-aware practice data in the existing account database.

Authentication is rechecked from an opaque login-session token in each SQL
transaction. Public snapshots omit job internals, file paths and audio bytes.
"""
from datetime import datetime, timezone
import hashlib
import io
import json
import secrets
import time
import uuid

import soundfile as sf


class Conflict(ValueError):
    pass


class Busy(Conflict):
    pass


class PreparationError(ValueError):
    def __init__(self,error):
        super().__init__(error['user_message'])
        self.error=error


class SessionMethods:
    def init_practice(self):
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS practice_state (
                    attempt_id TEXT PRIMARY KEY REFERENCES attempts(id), body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS practice_assets (
                    id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES attempts(id),
                    role TEXT NOT NULL, revision INTEGER NOT NULL, data BLOB NOT NULL);
            ''')

    def _auth(self, db, token):
        if not isinstance(token, str):
            raise PermissionError()
        row = db.execute('SELECT user_id FROM sessions WHERE token_hash=? AND expires>?',
                         (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        if not row:
            raise PermissionError()
        return row['user_id']

    def _practice(self, db, token, identity):
        owner = self._auth(db, token)
        row = db.execute('''SELECT p.body FROM practice_state p JOIN attempts a ON a.id=p.attempt_id
                            WHERE a.id=? AND a.user_id=? AND a.deleted=0''', (identity, owner)).fetchone()
        if not row:
            raise PermissionError()
        return json.loads(row['body'])

    def _save_practice(self, db, state):
        state['updated_at'] = datetime.now(timezone.utc).isoformat()
        db.execute('UPDATE practice_state SET body=? WHERE attempt_id=?',
                   (json.dumps(state, ensure_ascii=False, allow_nan=False), state['attempt_id']))
        active = [state[k+'_status'] for k in ('transcription','analysis','generation')]
        status = 'processing' if 'processing' in active else 'queued' if 'queued' in active else (
            'completed' if state['analysis_status']=='completed' else 'failed' if state['analysis_status']=='failed' else 'ready')
        db.execute('UPDATE attempts SET sentence=?,status=?,message=?,result=? WHERE id=? AND deleted=0',
            (state.get('confirmed_text') or state.get('recognized_text') or 'Free speech', status,
             'Review your transcript before analysis.' if status=='ready' else 'Practice '+status+'.',
             json.dumps(self.public_practice(state)) if state['analysis_status']=='completed' else None, state['attempt_id']))

    @staticmethod
    def public_practice(state):
        return {k:v for k,v in state.items() if not k.startswith('_')}

    def create_session(self, token, *, input_mode, target_accent, lesson_id=None):
        if input_mode not in {'custom_text','free_speech'} or target_accent!='en-US-general-american':
            raise ValueError('Use custom text or free speech with General American English.')
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            owner = self._auth(db,token)
            identity = uuid.uuid4().hex
            state = dict(schema_version=1,user_id=owner,attempt_id=identity,input_mode=input_mode,
                recognized_text=None,confirmed_text=None,target_accent=target_accent,learner_audio_id=None,
                analysis_status=None,sound_results=[],generation_status=None,generated_audio_id=None,
                generated_audio_type=None,timings={},input_revision=1,lesson_id=None,created_at=now,
                updated_at=now,transcription_status=None,errors={},limitations=[],_jobs={},_transcription=None)
            db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?,?,0)',
                       (identity,owner,'','Free speech',time.time(),'ready','Attach a recording.',None,None))
            db.execute('INSERT INTO practice_state VALUES (?,?)',(identity,json.dumps(state)))
        return self.public_practice(state)

    def get_session(self, token, identity):
        with self.connect() as db:
            return self.public_practice(self._practice(db,token,identity))

    @staticmethod
    def _revision(state, expected):
        if type(expected) is not int or state['input_revision'] != expected:
            raise Conflict('The attempt changed. Reload and try again.')

    @staticmethod
    def _invalidate(state, *, audio=False):
        state['input_revision'] += 1
        for kind, job in state['_jobs'].items():
            if job['status'] in {'queued','processing'}:
                job['status']='cancelled'
                state[kind+'_status']='cancelled'
        for kind in ('analysis','generation'):
            state[kind+'_status']=None
        errors={} if audio else {k:v for k,v in state['errors'].items() if k=='transcription'}
        timings={} if audio else {k:v for k,v in state['timings'].items() if k=='transcription'}
        state.update(sound_results=[],generated_audio_id=None,generated_audio_type=None,errors=errors,timings=timings,limitations=[])
        if audio:
            state.update(recognized_text=None,confirmed_text=None,transcription_status=None,_transcription=None)

    def attach_session_recording(self, token, identity, data, *, expected_revision):
        with self.connect() as db:
            self._practice(db,token,identity)
        if not isinstance(data,bytes) or len(data)>10*1024*1024:
            raise ValueError('Use a WAV within five seconds and 10 MB.')
        info=sf.info(io.BytesIO(data))
        if info.format not in {'WAV','WAVEX','RF64'} or not 0<info.duration<=5 or info.channels>8 or info.samplerate>192000:
            raise ValueError('Use a WAV within five seconds and 10 MB.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state=self._practice(db,token,identity)
            self._revision(state,expected_revision)
            if db.execute("SELECT 1 FROM practice_assets WHERE role='synthetic_example' AND data=? LIMIT 1",(data,)).fetchone():
                raise ValueError('Upload your original recording, not a generated example.')
            self._invalidate(state,audio=True)
            db.execute('DELETE FROM practice_assets WHERE attempt_id=?',(identity,))
            asset=uuid.uuid4().hex
            db.execute('INSERT INTO practice_assets VALUES (?,?,?,?,?)',(asset,identity,'learner',state['input_revision'],data))
            state['learner_audio_id']=asset
            state['_audio_hash']=hashlib.sha256(data).hexdigest()
            self._save_practice(db,state)
            return self.public_practice(state)

    def confirm_session_transcript(self,token,identity,text,*,expected_revision):
        with self.connect() as db:
            self._practice(db,token,identity)
        from transcript_input import prepare_transcript
        from phoneme_scoring.align_audio import load_settings
        prepared=prepare_transcript(text,load_settings(self.settings_path))
        if not prepared['ok']:
            raise PreparationError(prepared['error'])
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state=self._practice(db,token,identity)
            self._revision(state,expected_revision)
            if not state['learner_audio_id']:
                raise ValueError('Attach your recording first.')
            if state['confirmed_text']!=text.strip():
                self._invalidate(state)
                db.execute("DELETE FROM practice_assets WHERE attempt_id=? AND role!='learner'",(identity,))
                state['confirmed_text']=text.strip()
            self._save_practice(db,state)
            return self.public_practice(state)

    def begin_practice_job(self, token, identity, revision, kind):
        if kind not in {'transcription','analysis','generation'}:
            raise ValueError('Unknown job.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state=self._practice(db,token,identity)
            self._revision(state,revision)
            if not state['learner_audio_id']:
                raise ValueError('Attach your recording first.')
            if kind!='transcription' and not state['confirmed_text']:
                raise ValueError('Confirm the transcript first.')
            old=state['_jobs'].get(kind)
            if old and old['revision']==revision and old['status'] in {'queued','processing'}:
                return dict(ok=True,attempt_id=identity,input_revision=revision,job_id=old['id'],status='queued',_already_active=True)
            job=uuid.uuid4().hex
            state['_jobs'][kind]=dict(id=job,revision=revision,status='queued',created=time.monotonic())
            state[kind+'_status']='queued'
            state['errors'].pop(kind,None)
            if kind=='generation':
                state.update(generated_audio_id=None,generated_audio_type=None)
                db.execute("DELETE FROM practice_assets WHERE attempt_id=? AND role='synthetic_example'",(identity,))
            if kind=='analysis': state['sound_results']=[]
            self._save_practice(db,state)
            return dict(ok=True,attempt_id=identity,input_revision=revision,job_id=job,status='queued')

    def active_job_receipt(self,token,identity,revision,kind):
        if kind not in {'transcription','analysis','generation'}:raise ValueError('Unknown job.')
        with self.connect() as db:
            state=self._practice(db,token,identity);self._revision(state,revision)
            job=state['_jobs'].get(kind)
            if job and job['revision']==revision and job['status'] in {'queued','processing'}:
                return dict(ok=True,attempt_id=identity,input_revision=revision,job_id=job['id'],status='queued')
        return None

    def job_snapshot(self, token, identity, job_id, revision, kind):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state=self._practice(db,token,identity)
            self._revision(state,revision)
            job=state['_jobs'].get(kind)
            if not job or job['id']!=job_id or job['revision']!=revision or job['status']!='queued':
                raise Conflict('Job is no longer current.')
            job['status']='processing';state[kind+'_status']='processing'
            self._save_practice(db,state)
            asset=db.execute("SELECT data,role FROM practice_assets WHERE id=? AND attempt_id=?",(state['learner_audio_id'],identity)).fetchone()
            if not asset or asset['role']!='learner': raise PermissionError()
            return dict(state,job_id=job_id,learner_audio_role='learner',source_audio_sha256=state['_audio_hash'],
                        transcript_confirmed=bool(state['confirmed_text']),transcription=state['_transcription'],
                        _recording=bytes(asset['data']),_queued=job['created'])

    def publish_job(self, token, snapshot, kind, result, *, generated=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try: state=self._practice(db,token,snapshot['attempt_id'])
            except PermissionError: return False
            job=state['_jobs'].get(kind)
            if (state['input_revision']!=snapshot['input_revision'] or not job or job['id']!=snapshot['job_id']
                or job['status']!='processing' or state['learner_audio_id']!=snapshot['learner_audio_id']
                or state['confirmed_text']!=snapshot['confirmed_text']): return False
            successful=result.get('ok',result.get('status')=='completed')
            job['status']='completed' if successful else 'failed';state[kind+'_status']=job['status']
            if not successful:
                state['errors'][kind]=result.get('error') or dict(code='MODEL_UNAVAILABLE',user_message='Processing failed. Please retry.',retryable=True)
            elif kind=='transcription':
                state['recognized_text']=result['recognized_text'];state['_transcription']=result
            elif kind=='analysis':
                state['sound_results']=result['sound_results'];state['limitations']=result.get('limitations',[])
            elif generated is not None:
                asset=uuid.uuid4().hex
                db.execute('INSERT INTO practice_assets VALUES (?,?,?,?,?)',(asset,state['attempt_id'],'synthetic_example',state['input_revision'],generated))
                state.update(generated_audio_id=asset,generated_audio_type='synthetic_example')
            if result.get('timings'): state['timings'].update(result['timings'])
            self._save_practice(db,state)
            return True

    def session_asset(self,token,identity,asset_id):
        with self.connect() as db:
            state=self._practice(db,token,identity)
            if asset_id not in {state['learner_audio_id'],state['generated_audio_id']} or asset_id is None:
                raise PermissionError()
            row=db.execute('SELECT data,role,revision FROM practice_assets WHERE id=? AND attempt_id=?',(asset_id,identity)).fetchone()
            if not row or (row['role']!='learner' and row['revision']!=state['input_revision']): raise PermissionError()
            return bytes(row['data'])

    def list_sessions(self,token,*,limit=50,cursor=None):
        if type(limit) is not int or not 1<=limit<=50:raise ValueError('Use a limit between 1 and 50.')
        offset=int(cursor) if cursor is not None else 0
        if offset<0:raise ValueError('Invalid history cursor.')
        with self.connect() as db:
            owner=self._auth(db,token)
            rows=db.execute('SELECT p.body FROM practice_state p JOIN attempts a ON a.id=p.attempt_id WHERE a.user_id=? AND a.deleted=0 ORDER BY a.created DESC LIMIT ? OFFSET ?',(owner,limit+1,offset)).fetchall()
            return dict(attempts=[self.public_practice(json.loads(r['body'])) for r in rows[:limit]],next_cursor=str(offset+limit) if len(rows)>limit else None)

    def delete_session(self,token,identity):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self._practice(db,token,identity)
            db.execute("UPDATE attempts SET deleted=1,audio=NULL,result=NULL,status='cancelled' WHERE id=?",(identity,))
            db.execute('DELETE FROM practice_assets WHERE attempt_id=?',(identity,))
            db.execute('DELETE FROM practice_state WHERE attempt_id=?',(identity,))
        return dict(ok=True)

    def recover_practice(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute('SELECT body FROM practice_state').fetchall():
                state=json.loads(row['body'])
                changed=False
                for kind,job in state['_jobs'].items():
                    if job['status'] in {'queued','processing'}:
                        job['status']='failed';state[kind+'_status']='failed';changed=True
                        state['errors'][kind]=dict(code='MODEL_UNAVAILABLE',user_message='The app restarted before this job finished. Please retry.',retryable=True)
                if changed: self._save_practice(db,state)
