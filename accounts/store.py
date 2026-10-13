"""SQLite transactions for accounts, opaque login sessions and private attempts."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from accounts.sessions import SessionMethods

GOALS = ('TH', 'IH', 'AE')


class Store(SessionMethods):
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'accounts.sqlite3'
        self.hasher = PasswordHasher()
        self.dummy_hash = self.hasher.hash(secrets.token_urlsafe(24))
        self.settings_path = Path(__file__).resolve().parents[1] / 'phoneme_scoring/settings.json'
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL, display_name TEXT NOT NULL,
                    goals TEXT NOT NULL DEFAULT '[]');
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    csrf TEXT NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    prompt_id TEXT NOT NULL, sentence TEXT NOT NULL, created REAL NOT NULL,
                    status TEXT NOT NULL, message TEXT NOT NULL, audio BLOB,
                    result TEXT, deleted INTEGER NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS owner_attempts ON attempts(user_id, created);
                CREATE TABLE IF NOT EXISTS auth_limits (
                    key TEXT PRIMARY KEY, started REAL NOT NULL, count INTEGER NOT NULL);
            ''')
        try:
            self.db.chmod(0o600)
        except OSError:
            pass
        self.init_practice()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA secure_delete=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def throttle(self, key):
        """Bound credential attempts per source and per account in a rolling window."""
        key = hashlib.sha256(key.encode()).hexdigest()
        now = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM auth_limits WHERE started < ?', (now - 900,))
            row = db.execute('SELECT count FROM auth_limits WHERE key=?', (key,)).fetchone()
            if row and row['count'] >= 30:
                return False
            db.execute('INSERT INTO auth_limits VALUES (?, ?, 1) ON CONFLICT(key) DO UPDATE SET count=count+1', (key, now))
            return True

    def register(self, username, password, display_name):
        username = username.strip().lower()
        display_name = display_name.strip()
        if not re.fullmatch(r'[a-z0-9_]{3,32}', username):
            raise ValueError('Use 3–32 letters, numbers or underscores for your username.')
        if not 12 <= len(password) <= 128:
            raise ValueError('Use a password between 12 and 128 characters.')
        if not 1 <= len(display_name) <= 60:
            raise ValueError('Enter a display name of 1–60 characters.')
        user_id = uuid.uuid4().hex
        hashed = self.hasher.hash(password)
        try:
            with self.connect() as db:
                db.execute('INSERT INTO users (id,username,password,display_name) VALUES (?,?,?,?)',
                           (user_id, username, hashed, display_name))
        except sqlite3.IntegrityError:
            raise ValueError('That username is already taken.') from None
        return user_id

    def login(self, username, password):
        if len(password) > 128:
            return None
        with self.connect() as db:
            row = db.execute('SELECT * FROM users WHERE username=?', (username.strip().lower(),)).fetchone()
        try:
            self.hasher.verify(row['password'] if row else self.dummy_hash, password)
        except (VerificationError, InvalidHashError):
            return None
        if not row:
            return None
        if self.hasher.check_needs_rehash(row['password']):
            with self.connect() as db:
                db.execute('UPDATE users SET password=? WHERE id=?', (self.hasher.hash(password), row['id']))
        return row['id']

    def new_session(self, owner):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(), owner, csrf, time.time()+7*86400))
        return token

    def session(self, token):
        if not token or len(token) > 128:
            return None
        with self.connect() as db:
            row = db.execute('''SELECT u.id,u.username,u.display_name,u.goals,s.csrf
                FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.token_hash=? AND s.expires>?''',
                (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        if not row:
            return None
        user = dict(row)
        user['goals'] = json.loads(user['goals'])
        return user

    def logout(self, token):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            owner=db.execute('SELECT user_id FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))
            if owner:
                rows=db.execute('SELECT p.body FROM practice_state p JOIN attempts a ON a.id=p.attempt_id WHERE a.user_id=? AND a.deleted=0',(owner['user_id'],)).fetchall()
                for row in rows:
                    state=json.loads(row['body']);changed=False
                    for kind,job in state['_jobs'].items():
                        if job['status'] in {'queued','processing'}:
                            job['status']='cancelled';state[kind+'_status']='cancelled';changed=True
                    if changed:self._save_practice(db,state)

    def profile(self, owner, display_name, goals):
        if not isinstance(display_name, str) or not 1 <= len(display_name.strip()) <= 60:
            raise ValueError('Enter a display name of 1–60 characters.')
        if not isinstance(goals, list) or any(g not in GOALS for g in goals):
            raise ValueError('Choose one of the available practice sounds.')
        with self.connect() as db:
            db.execute('UPDATE users SET display_name=?,goals=? WHERE id=?',
                       (display_name.strip(), json.dumps(list(dict.fromkeys(goals))), owner))

    def create_attempt(self, owner, prompt, audio):
        identity = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM attempts WHERE user_id=? AND deleted=0 AND status IN ('queued','processing')", (owner,)).fetchone():
                raise ValueError('You already have a recording waiting or being analyzed. Open History to follow it.')
            db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?,?,0)',
                       (identity, owner, prompt['id'], prompt['text'], time.time(), 'queued',
                        'Your recording is saved and waiting for analysis.', audio, None))
        return identity

    def get_attempt(self, owner, identity, audio=False):
        fields = '*' if audio else 'id,prompt_id,sentence,created,status,message,result'
        with self.connect() as db:
            row = db.execute(f'SELECT {fields} FROM attempts WHERE id=? AND user_id=? AND deleted=0', (identity, owner)).fetchone()
        if row is None:
            raise LookupError('Attempt not found.')
        row = dict(row)
        if row.get('result'):
            row['result'] = json.loads(row['result'])
        return row

    def history(self, owner):
        with self.connect() as db:
            rows = db.execute('''SELECT id,prompt_id,sentence,created,status,message FROM attempts
                WHERE user_id=? AND deleted=0 ORDER BY created DESC LIMIT 100''', (owner,)).fetchall()
        return [dict(r) for r in rows]

    def progress(self, owner, identity, message):
        with self.connect() as db:
            return db.execute("UPDATE attempts SET status='processing',message=? WHERE id=? AND user_id=? AND deleted=0 AND status IN ('queued','processing')",
                              (message, identity, owner)).rowcount == 1

    def finish(self, owner, identity, result=None, error=None):
        status = 'failed' if error or (result and result.get('overall_status') == 'failed') else 'completed'
        message = error or ('Processing failed. Your recording is saved; check the result for details.' if status == 'failed'
                            else 'Analysis finished. Recording and results are saved to your account.')
        with self.connect() as db:
            return db.execute("""UPDATE attempts SET status=?,message=?,result=? WHERE id=? AND user_id=?
                AND deleted=0 AND status IN ('queued','processing')""",
                (status, message, json.dumps(result, ensure_ascii=False, allow_nan=False) if result else None, identity, owner)).rowcount == 1

    def delete_attempt(self, owner, identity):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute("UPDATE attempts SET deleted=1,audio=NULL,result=NULL,message='',status='cancelled' WHERE id=? AND user_id=? AND deleted=0", (identity, owner)).rowcount
            if changed:
                db.execute('DELETE FROM practice_assets WHERE attempt_id=?',(identity,))
                db.execute('DELETE FROM practice_state WHERE attempt_id=?',(identity,))
        if not changed:
            raise LookupError('Attempt not found.')

    def recover_interrupted(self):
        with self.connect() as db:
            db.execute("""UPDATE attempts SET status='failed',message='The app restarted before analysis finished. Your recording is saved; please record or upload again.'
                WHERE deleted=0 AND status IN ('queued','processing')""")
        self.recover_practice()

    def suggestions(self, owner, goals):
        with self.connect() as db:
            rows = db.execute("SELECT result FROM attempts WHERE user_id=? AND deleted=0 AND status='completed' AND result IS NOT NULL ORDER BY created DESC LIMIT 30", (owner,)).fetchall()
        phones = []
        for row in rows:
            result=json.loads(row['result'])
            targets=result.get('target_assessment', {}).get('targets', [])
            targets=targets+[dict(expected_phone=t.get('expected_phone'),status='alternative_favored' if t.get('outcome')=='practice' else 'insufficient_evidence') for t in result.get('sound_results',[])]
            for target in targets:
                phone = target.get('expected_phone')
                if target.get('status') == 'alternative_favored' and phone in GOALS and phone not in phones and (not goals or phone in goals):
                    phones.append(phone)
        return phones[:3]
