"""Authenticated website and private playback; no Gradio file cache is exposed."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import html
import io
import json
import logging
import os
from pathlib import Path
import secrets
import shutil
import tempfile
import threading

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware
import numpy as np
import soundfile as sf

from accounts.store import Store, GOALS
from accounts.sessions import Conflict, Busy, PreparationError
from accounts.practice_jobs import PracticeJobs
from site_pages import ROOT, page_html

COOKIE = 'accent_session'
MAX_AUDIO = 10 * 1024 * 1024


def clean_result(value):
    """Keep diagnostic data but omit internal paths/settings before download."""
    if isinstance(value, dict):
        return {k: clean_result(v) for k, v in value.items()
                if k not in {'settings', 'audio_paths', 'results_path', 'path', 'wav_path', 'output_dir', 'textgrid_path', 'samples','command','run_dir','corpus_dir'}}
    if isinstance(value, list):
        return [clean_result(v) for v in value]
    return value


def remove_private_work(path, root):
    path=Path(path).resolve();root=Path(root).resolve()
    if not path.is_relative_to(root) or path==root:
        raise ValueError('Refusing to remove files outside private work storage.')
    shutil.rmtree(path,ignore_errors=True)


class Jobs:
    def __init__(self, store, analyzer):
        self.store, self.analyzer = store, analyzer
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='private-analysis')
        self.slots = threading.BoundedSemaphore(8)

    def submit(self, owner, identity):
        self.pool.submit(self.run, owner, identity)

    def run(self, owner, identity):
        folder = None
        try:
            attempt = self.store.get_attempt(owner, identity, audio=True)
            if not self.store.progress(owner, identity, 'Preparing your recording'):
                return
            work = self.store.root / 'work'
            work.mkdir(exist_ok=True)
            folder = Path(tempfile.mkdtemp(prefix='attempt-', dir=work))
            recording = folder / 'learner.wav'
            recording.write_bytes(attempt['audio'])
            result = self.analyzer(str(recording), attempt['prompt_id'], compare_reference=False,
                output_root=str(folder / 'results'),
                progress_callback=lambda message: self.store.progress(owner, identity, message))
            self.store.finish(owner, identity, clean_result(result))
        except LookupError:
            pass  # Deleted while queued: no file or result is recreated.
        except TimeoutError:
            self.store.finish(owner, identity, error='Analysis timed out. Your recording is saved. Please try again.')
        except Exception:
            logging.exception('Private attempt processing failed')
            self.store.finish(owner, identity, error='Analysis could not finish. Your recording is saved. Check the local app console and try again.')
        finally:
            if folder:
                remove_private_work(folder,self.store.root/'work')
            self.slots.release()

    def close(self):
        self.pool.shutdown(wait=True)


def private_site(data_root=None, analyzer=None, prompts=None, speech=None, generator=None):
    if analyzer is None:
        from analysis_service import run_attempt
        analyzer = run_attempt
    if prompts is None:
        from pipeline import load_prompts
        prompts = load_prompts()
    catalog = {p['id']: p for p in prompts}
    store = Store(data_root or os.environ.get('ACCENT_COACH_DATA_DIR', ROOT / 'private_data'))
    jobs = Jobs(store, analyzer)
    practice_jobs = PracticeJobs(store,speech,generator,pool=jobs.pool,slots=jobs.slots)

    @asynccontextmanager
    async def lifespan(app):
        store.recover_interrupted()
        # Only this private site's expired intermediate jobs; never old runs/.
        work = store.root / 'work'
        if work.exists():
            remove_private_work(work,store.root)
        yield
        jobs.close()
        from analysis_service import SERVICE
        SERVICE.close()

    site = FastAPI(title='Accent Coach', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    site.state.store, site.state.jobs, site.state.practice_jobs = store, jobs, practice_jobs
    site.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', '[::1]'])

    @site.middleware('http')
    async def private_headers(request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith('/site-assets/'):
            response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    def current(request):
        return store.session(request.cookies.get(COOKIE))

    def require(request):
        user = current(request)
        if not user:
            raise HTTPException(401, 'Sign in to continue.')
        return user

    def csrf(request, token, expected):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'Please reload this page and try again.')
        if not token or not expected or not secrets.compare_digest(str(token), str(expected)):
            raise HTTPException(403, 'Please reload this page and try again.')

    async def read_body(request, limit):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > limit:
                raise HTTPException(413, 'This upload is too large.')
        return bytes(data)

    async def json_body(request):
        try:
            value = json.loads(await read_body(request, 8192))
        except (ValueError, UnicodeError):
            raise HTTPException(422, 'Invalid request.') from None
        if not isinstance(value, dict):
            raise HTTPException(422, 'Invalid request.')
        return value

    def shell(title, body, path, user=None, token=None):
        account_nav = '<nav class="account-nav" aria-label="Account">'
        if user:
            account_nav += f'<span>Signed in as {html.escape(user["display_name"])}</span><form action="/logout" method="post"><input type="hidden" name="csrf" value="{user["csrf"]}"><button>Sign out</button></form>'
        account_nav += '</nav>'
        meta = f'<meta name="csrf-token" content="{html.escape(user["csrf"] if user else (token or ""), quote=True)}">'
        content = page_html(title, 'Private English pronunciation practice and saved recordings.',
                            (account_nav if user else '') + body, path)
        return content.replace('</head>', meta + '<link rel="stylesheet" href="/site-assets/accounts.css"><script src="/site-assets/accounts.js" defer></script></head>')

    def auth_page(request, signup=False, error='', status=200):
        token = request.cookies.get('accent_login_csrf') or secrets.token_urlsafe(32)
        if len(token) > 128:
            token = secrets.token_urlsafe(32)
        action, title = ('/signup', 'Create your account') if signup else ('/login', 'Sign in')
        name = '<label>Display name<input name="display_name" maxlength="60" autocomplete="name" required></label>' if signup else ''
        body = f'''<section class="account-card"><p class="eyebrow">Accent Coach</p><h1>{title}</h1>
        <p>Your profile, recordings and results are saved on this computer under your account.</p>
        <p class="form-error" role="alert">{html.escape(error)}</p>
        <form action="{action}" method="post" class="account-form">
        <input type="hidden" name="csrf" value="{html.escape(token, quote=True)}">{name}
        <label>Username<input name="username" minlength="3" maxlength="32" pattern="[A-Za-z0-9_]+" autocomplete="username" required></label>
        <label>Password<input type="password" name="password" minlength="12" maxlength="128" autocomplete="{'new-password' if signup else 'current-password'}" required></label>
        <p>Use at least 12 characters for your password.</p><button class="primary">{title}</button></form>
        <p><a href="{'/login' if signup else '/signup'}">{'Already have an account? Sign in' if signup else 'New here? Create an account'}</a></p></section>'''
        response = HTMLResponse(shell(title, body, action, token=token), status_code=status)
        response.set_cookie('accent_login_csrf', token, httponly=True, samesite='strict', secure=request.url.scheme == 'https', max_age=3600)
        return response

    @site.get('/')
    def home(request: Request):
        return RedirectResponse('/practice' if current(request) else '/login', status_code=303)

    @site.get('/login')
    def login_page(request: Request):
        return auth_page(request)

    @site.get('/signup')
    def signup_page(request: Request):
        return auth_page(request, signup=True)

    @site.post('/login')
    @site.post('/signup')
    async def authenticate(request: Request):
        from urllib.parse import parse_qs
        signup = request.url.path == '/signup'
        body = (await read_body(request, 8192)).decode('utf-8', errors='replace')
        form = {k: v[-1] for k, v in parse_qs(body).items()}
        csrf(request, form.get('csrf'), request.cookies.get('accent_login_csrf'))
        username, password = form.get('username', ''), form.get('password', '')
        source = request.client.host if request.client else 'local'
        if not store.throttle('ip:'+source) or not store.throttle('name:'+username.strip().lower()):
            return auth_page(request, signup, 'Too many sign-in attempts. Try again in 15 minutes.', 429)
        try:
            owner = store.register(username, password, form.get('display_name', '')) if signup else store.login(username, password)
        except ValueError as exc:
            return auth_page(request, signup, str(exc), 422)
        if owner is None:
            return auth_page(request, signup, 'Username or password is incorrect.', 401)
        if request.cookies.get(COOKIE):
            store.logout(request.cookies[COOKIE])
        response = RedirectResponse('/practice', status_code=303)
        response.set_cookie(COOKIE, store.new_session(owner), httponly=True, samesite='strict', secure=request.url.scheme == 'https', max_age=7*86400)
        response.delete_cookie('accent_login_csrf')
        return response

    @site.post('/logout')
    async def logout(request: Request):
        from urllib.parse import parse_qs
        user = require(request)
        data = parse_qs((await read_body(request, 8192)).decode('utf-8', errors='replace'))
        csrf(request, data.get('csrf', [''])[0], user['csrf'])
        store.logout(request.cookies.get(COOKIE, ''))
        response = RedirectResponse('/login', status_code=303)
        response.delete_cookie(COOKIE)
        return response

    @site.get('/practice')
    def practice(request: Request):
        user = current(request)
        if not user:
            return RedirectResponse('/login', status_code=303)
        options = ''.join(f'<option value="{html.escape(p["id"], quote=True)}">{html.escape(p["text"])}</option>' for p in prompts)
        body = f'''<h1>Practice English pronunciation.</h1><p>Choose a sentence, record up to five seconds, then review your saved result.</p>
        <section class="account-card"><label for="input-mode">Practice mode</label><select id="input-mode"><option value="preset">Preset lesson</option><option value="custom_text">My own sentence</option><option value="free_speech">Free speech</option></select>
        <label for="lesson">Practice sentence</label><select id="lesson">{options}</select>
        <label id="custom-label" hidden>My sentence (up to 12 words and 200 characters)<textarea id="custom-text" maxlength="200" rows="3"></textarea></label>
        <p id="lesson-hint"></p><audio id="example" controls></audio><p>Synthetic listening example; not used to score your voice.</p>
        <div class="record-actions"><button id="record">Record my voice</button><button id="stop" disabled>Stop recording</button></div>
        <label>Or upload a WAV<input id="recording-file" type="file" accept=".wav,audio/wav"></label>
        <audio id="preview" controls hidden></audio><button id="analyze" class="primary" disabled>Check and save my recording</button>
        <p id="practice-status" role="status" aria-live="polite">Your recordings and results will appear in My history.</p></section>
        <section id="attempt-result" class="account-card" hidden></section>
        <section id="session-panel" class="account-card" hidden></section>
        <section class="account-card"><h2>Practice next</h2><p id="suggestions">Set your practice goals in My profile.</p></section>'''
        return HTMLResponse(shell('English pronunciation practice', body, '/practice', user))

    @site.get('/profile')
    def profile_page(request: Request):
        user = current(request)
        if not user:
            return RedirectResponse('/login', status_code=303)
        goals = ''.join(f'<label class="goal"><input type="checkbox" name="goal" value="{g}" {"checked" if g in user["goals"] else ""}> {g}</label>' for g in GOALS)
        body = f'''<h1>My profile</h1><section class="account-card"><p>Username: <strong>{html.escape(user['username'])}</strong></p>
        <form id="profile-form" class="account-form"><label>Display name<input id="display-name" value="{html.escape(user['display_name'], quote=True)}" maxlength="60" required></label>
        <p>Target accent: General American English</p><fieldset><legend>Sounds I want to practice</legend>{goals}</fieldset>
        <p>TH as in think, IH as in ship, AE as in bad. Leave all unchecked for general suggestions.</p>
        <button class="primary">Save profile</button><p id="profile-status" role="status"></p></form></section>'''
        return HTMLResponse(shell('My profile', body, '/profile', user))

    @site.get('/history')
    def history_page(request: Request):
        user = current(request)
        if not user:
            return RedirectResponse('/login', status_code=303)
        body = '''<h1>My saved attempts</h1><p>Recordings and results stay here when you sign out or restart the app.</p>
        <p>Model feedback is experimental. Changes between attempts do not establish improvement.</p>
        <p id="history-status" role="status"></p><div id="history-list"></div><section id="attempt-result" class="account-card" hidden></section><section id="session-panel" class="account-card" hidden></section>'''
        return HTMLResponse(shell('My history', body, '/history', user))

    @site.get('/api/me')
    def me(request: Request):
        user = require(request)
        return {k: user[k] for k in ('username', 'display_name', 'goals')}

    @site.post('/api/profile')
    async def save_profile(request: Request):
        user = require(request)
        csrf(request, request.headers.get('x-csrf-token'), user['csrf'])
        body = await json_body(request)
        try:
            store.profile(user['id'], body.get('display_name'), body.get('goals'))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        return {'ok': True}

    @site.get('/api/lessons')
    def lessons(request: Request):
        require(request)
        return [{'id': p['id'], 'text': p['text'], 'hint': p.get('practice_tip', '')} for p in prompts]

    @site.get('/api/suggestions')
    def suggestions(request: Request):
        user = require(request)
        return {'phones': store.suggestions(user['id'], user['goals'])}

    @site.get('/api/attempts')
    def history(request: Request):
        return {'attempts': store.history(require(request)['id'])}

    @site.post('/api/attempts', status_code=202)
    async def analyze(request: Request, prompt_id: str):
        user = require(request)
        csrf(request, request.headers.get('x-csrf-token'), user['csrf'])
        if prompt_id not in catalog:
            raise HTTPException(422, 'Choose an available practice sentence.')
        if request.headers.get('content-type', '').split(';')[0] not in {'audio/wav', 'audio/x-wav'}:
            raise HTTPException(415, 'Upload a WAV recording.')
        audio = await read_body(request, MAX_AUDIO)
        try:
            info = sf.info(io.BytesIO(audio))
            if info.format not in {'WAV', 'WAVEX'} or info.frames <= 0 or info.duration > 5 or info.channels > 2:
                raise ValueError()
            samples, _ = sf.read(io.BytesIO(audio))
            if len(samples) != info.frames or not np.isfinite(samples).all():
                raise ValueError()
        except Exception:
            raise HTTPException(422, 'Use a valid mono or stereo WAV recording, at most five seconds and 10 MB.') from None
        with store.connect() as db:
            if db.execute("SELECT 1 FROM practice_assets WHERE role='synthetic_example' AND data=? LIMIT 1",(audio,)).fetchone():
                raise HTTPException(422,'Upload your original recording, not a generated example.')
        if not jobs.slots.acquire(blocking=False):
            raise HTTPException(503, 'The analysis queue is full. Please try again shortly.')
        try:
            identity = store.create_attempt(user['id'], catalog[prompt_id], audio)
        except ValueError as exc:
            jobs.slots.release()
            raise HTTPException(409, str(exc)) from None
        except Exception:
            jobs.slots.release()
            raise
        try:
            jobs.submit(user['id'], identity)
        except Exception:
            jobs.slots.release()
            store.finish(user['id'], identity, error='Analysis could not start. Your recording is saved; try again.')
            raise HTTPException(503, 'Analysis could not start; your recording is saved.') from None
        return {'attempt_id': identity, 'status': 'queued'}

    def own_attempt(request, identity, audio=False):
        try:
            return store.get_attempt(require(request)['id'], identity, audio=audio)
        except LookupError:
            raise HTTPException(404, 'Attempt not found.') from None

    @site.get('/api/attempts/{identity}')
    def get_attempt(request: Request, identity: str):
        return own_attempt(request, identity)

    @site.get('/api/attempts/{identity}/audio')
    def get_audio(request: Request, identity: str):
        data = own_attempt(request, identity, audio=True)['audio']
        return Response(data, media_type='audio/wav', headers={'Content-Disposition': 'inline; filename="my-recording.wav"'})

    @site.get('/api/attempts/{identity}/result')
    def download_result(request: Request, identity: str):
        result = own_attempt(request, identity)['result']
        if result is None:
            raise HTTPException(409, 'No analysis result is available yet.')
        return JSONResponse(result, headers={'Content-Disposition': 'attachment; filename="my-analysis.json"'})

    @site.delete('/api/attempts/{identity}')
    def delete(request: Request, identity: str):
        user = require(request)
        csrf(request, request.headers.get('x-csrf-token'), user['csrf'])
        try:
            store.delete_attempt(user['id'], identity)
        except LookupError:
            raise HTTPException(404, 'Attempt not found.') from None
        return {'ok': True}

    def practice_error(exc, code='UNSUPPORTED_TEXT'):
        if isinstance(exc,PreparationError):
            return JSONResponse(dict(ok=False,error=exc.error),status_code=503 if exc.error['code']=='MODEL_UNAVAILABLE' else 422)
        if isinstance(exc,PermissionError):
            return JSONResponse({'ok':False,'error':{'code':'ATTEMPT_UNAVAILABLE','user_message':'This attempt is unavailable.','retryable':False}},status_code=404)
        conflict=isinstance(exc,Conflict)
        busy=isinstance(exc,Busy)
        return JSONResponse({'ok':False,'error':{'code':'BUSY' if busy else 'REVISION_CONFLICT' if conflict else code,'user_message':str(exc),'retryable':busy}},status_code=503 if busy else 409 if conflict else 422)

    @site.post('/api/sessions')
    async def create_practice(request: Request):
        user=require(request);csrf(request,request.headers.get('x-csrf-token'),user['csrf'])
        body=await json_body(request)
        try:
            return store.create_session(request.cookies.get(COOKIE),input_mode=body.get('input_mode'),
                target_accent=body.get('target_accent','en-US-general-american'))
        except (PermissionError,ValueError) as exc: return practice_error(exc)

    @site.get('/api/sessions')
    def list_practice(request:Request,limit:int=50,cursor:str=None):
        require(request)
        try:return store.list_sessions(request.cookies.get(COOKIE),limit=limit,cursor=cursor)
        except (PermissionError,ValueError) as exc:return practice_error(exc)

    @site.get('/api/sessions/{identity}')
    def practice_snapshot(request:Request,identity:str):
        require(request)
        try: return store.get_session(request.cookies.get(COOKIE),identity)
        except PermissionError as exc: return practice_error(exc)

    @site.post('/api/sessions/{identity}/recording')
    async def practice_recording(request:Request,identity:str,expected_revision:int):
        user=require(request);csrf(request,request.headers.get('x-csrf-token'),user['csrf'])
        if request.headers.get('content-type','').split(';')[0] not in {'audio/wav','audio/x-wav'}:
            return practice_error(ValueError('Upload a WAV recording.'),'INVALID_AUDIO')
        data=await read_body(request,MAX_AUDIO)
        token=request.cookies.get(COOKIE)
        try:
            state=store.attach_session_recording(token,identity,data,expected_revision=expected_revision)
            practice_jobs.submit(token,identity,state['input_revision'],'transcription')
            return store.get_session(token,identity)
        except (PermissionError,ValueError,RuntimeError) as exc: return practice_error(exc,'INVALID_AUDIO')

    @site.post('/api/sessions/{identity}/confirm')
    async def practice_confirm(request:Request,identity:str):
        user=require(request);csrf(request,request.headers.get('x-csrf-token'),user['csrf'])
        body=await json_body(request)
        try:
            return store.confirm_session_transcript(request.cookies.get(COOKIE),identity,body.get('text'),expected_revision=body.get('expected_revision'))
        except (PermissionError,ValueError) as exc: return practice_error(exc)

    @site.post('/api/sessions/{identity}/jobs/{kind}',status_code=202)
    async def practice_submit(request:Request,identity:str,kind:str):
        user=require(request);csrf(request,request.headers.get('x-csrf-token'),user['csrf'])
        body=await json_body(request)
        try:
            return practice_jobs.submit(request.cookies.get(COOKIE),identity,body.get('input_revision'),kind)
        except (PermissionError,ValueError) as exc: return practice_error(exc,'TRANSCRIPT_CONFIRMATION_REQUIRED')

    @site.get('/api/sessions/{identity}/audio/{asset_id}')
    def practice_audio(request:Request,identity:str,asset_id:str):
        require(request)
        try: return Response(store.session_asset(request.cookies.get(COOKIE),identity,asset_id),media_type='audio/wav')
        except PermissionError as exc: return practice_error(exc)

    return site
