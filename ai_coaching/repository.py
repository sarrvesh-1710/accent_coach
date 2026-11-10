"""Use the existing private SQLite store; never read audio or duplicate sessions."""
import json
import sqlite3
import time
from contextlib import contextmanager

from .evidence import base_version,digest


class StaleEvidence(ValueError):pass


class Repository:
    def __init__(self,store):
        self.store=store
        self.ready=False
        try:
            with self.connect() as db:
                db.executescript('''CREATE TABLE IF NOT EXISTS coach_explanations (
                user_id TEXT NOT NULL REFERENCES users(id),attempt_id TEXT NOT NULL REFERENCES attempts(id),
                cache_key TEXT NOT NULL,body TEXT NOT NULL,created REAL NOT NULL,
                PRIMARY KEY(user_id,attempt_id,cache_key));
                CREATE TRIGGER IF NOT EXISTS delete_attempt_coaching AFTER UPDATE OF deleted ON attempts
                WHEN NEW.deleted=1 BEGIN DELETE FROM coach_explanations WHERE attempt_id=NEW.id AND user_id=NEW.user_id; END;''')
            self.ready=True
        except sqlite3.OperationalError:
            # An optional cache migration must not take down the speech app.
            # Do not retry/write from the base-result request path.
            pass

    @contextmanager
    def connect(self):
        with self.store.connect() as db:
            db.execute('PRAGMA busy_timeout=50')
            yield db

    def _snapshot(self,db,token,identity):
        if not self.ready:raise sqlite3.OperationalError('Optional coaching storage unavailable')
        owner=self.store._auth(db,token)
        row=db.execute('''SELECT a.id,a.prompt_id,a.sentence,a.status,a.message,a.result,p.body
                          FROM attempts a LEFT JOIN practice_state p ON a.id=p.attempt_id
                          WHERE a.id=? AND a.user_id=? AND a.deleted=0''',(identity,owner)).fetchone()
        if not row:raise PermissionError('Attempt unavailable')
        if row['body']:data=json.loads(row['body']);data={k:v for k,v in data.items() if not k.startswith('_')}
        else:data=dict(row);data.pop('body');data['result']=json.loads(data['result']) if data['result'] else None
        plan_row=db.execute('SELECT body FROM lesson_plans WHERE user_id=?',(owner,)).fetchone();plan=None
        if plan_row:
            body=json.loads(plan_row['body'])
            completed=[r['prompt_id'] for r in db.execute('''SELECT DISTINCT p.prompt_id FROM lesson_plan_steps p
                JOIN attempts a ON a.id=p.attempt_id AND a.user_id=p.user_id
                WHERE p.user_id=? AND p.plan_id=? AND a.deleted=0 AND a.status='completed' ''',(owner,body['plan_id']))]
            plan=dict(started=True,kind=body.get('kind','practice'),steps=body.get('steps',[]),completed=completed)
        return dict(owner=owner,attempt_id=identity,data=data,base_version=base_version(data),plan=plan)

    def snapshot(self,token,identity):
        with self.connect() as db:return self._snapshot(db,token,identity)

    def cached(self,token,identity,key,expected_version,expected_plan):
        with self.connect() as db:
            snap=self._snapshot(db,token,identity)
            if snap['base_version']!=expected_version or digest(snap['plan'])!=expected_plan:raise StaleEvidence('Evidence changed')
            row=db.execute('SELECT body FROM coach_explanations WHERE user_id=? AND attempt_id=? AND cache_key=?',(snap['owner'],identity,key)).fetchone()
            return json.loads(row['body']) if row else None

    def publish(self,token,snapshot,key,output,expected_plan):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=self._snapshot(db,token,snapshot['attempt_id'])
            if current['base_version']!=snapshot['base_version'] or digest(current['plan'])!=expected_plan:
                raise StaleEvidence('Evidence changed')
            # Only validated short output is saved; no prompts, credentials or raw provider output.
            db.execute('INSERT OR REPLACE INTO coach_explanations VALUES (?,?,?,?,?)',
                (current['owner'],snapshot['attempt_id'],key,json.dumps(output,ensure_ascii=False),time.time()))
            # Bound retained versions per attempt without touching any base recording/results.
            db.execute('''DELETE FROM coach_explanations WHERE user_id=? AND attempt_id=? AND rowid NOT IN
                (SELECT rowid FROM coach_explanations WHERE user_id=? AND attempt_id=? ORDER BY created DESC LIMIT 3)''',
                (current['owner'],snapshot['attempt_id'],current['owner'],snapshot['attempt_id']))
