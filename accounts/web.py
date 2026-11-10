"""Authenticated website and private playback; no Gradio file cache is exposed."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import asyncio
import html
import hashlib
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
from site_pages import ROOT, ASSETS, page_html

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


def private_site(data_root=None, analyzer=None, prompts=None, speech=None, generator=None, coaching_config=None, coaching_provider=None):
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
    from ai_coaching.service import CoachingService
    coaching=CoachingService(store,catalog,coaching_config,coaching_provider)

    @asynccontextmanager
    async def lifespan(app):
        store.recover_interrupted()
        # Only this private site's expired intermediate jobs; never old runs/.
        work = store.root / 'work'
        if work.exists():
            remove_private_work(work,store.root)
        yield
        await coaching.close()
        jobs.close()
        practice_jobs.close()
        from analysis_service import SERVICE
        SERVICE.close()

    site = FastAPI(title='Accent Coach', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    site.state.store, site.state.jobs, site.state.practice_jobs = store, jobs, practice_jobs
    site.state.result_coaching=coaching
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

    async def json_body(request, allow_empty=False):
        try:
            raw = await read_body(request, 8192)
            value = {} if allow_empty and not raw else json.loads(raw)
        except (ValueError, UnicodeError):
            raise HTTPException(422, 'Invalid request.') from None
        if not isinstance(value, dict):
            raise HTTPException(422, 'Invalid request.')
        return value

    def account_menu(user):
        if not user: return ''
        return f'<details class="account-menu"><summary><span id="signed-in-name">Signed in as {html.escape(user["display_name"])}</span></summary><div class="account-menu-panel"><a href="/profile">My profile</a><a href="/history">My history</a><form action="/logout" method="post"><input type="hidden" name="csrf" value="{user["csrf"]}"><button>Sign out</button></form></div></details>'

    def decorate_information_page(request, content):
        user=current(request)
        if not user: return content
        revision=hashlib.sha256((ASSETS/'ui-polish.css').read_bytes()).hexdigest()[:12]
        return content.replace('</header>',account_menu(user)+'</header>',1).replace('</head>',f'<link rel="stylesheet" href="/site-assets/accounts.css"><link rel="stylesheet" href="/site-assets/ui-polish.css?v={revision}"></head>')

    site.state.decorate_information_page=decorate_information_page

    def shell(title, body, path, user=None, token=None):
        account_nav = account_menu(user)
        meta = f'<meta name="csrf-token" content="{html.escape(user["csrf"] if user else (token or ""), quote=True)}">'
        content = page_html(title, 'Private English pronunciation practice and saved recordings.',
                            body, path)
        if user:
            content = content.replace('</header>', account_nav + '</header>', 1).replace('class="document"', 'class="document account-document"', 1)
        css_version = hashlib.sha256((ASSETS / 'accounts.css').read_bytes()).hexdigest()[:12]
        js_version = hashlib.sha256((ASSETS / 'accounts.js').read_bytes()).hexdigest()[:12]
        polish_version = hashlib.sha256((ASSETS / 'ui-polish.css').read_bytes()).hexdigest()[:12]
        coach_settings=coaching.config.public()
        coach_meta='<meta name="coach-settings" content="'+html.escape(json.dumps(coach_settings),quote=True)+'">'
        coach_script=''
        if coach_settings['available']:
            coach_version=hashlib.sha256((ASSETS/'result_coach.js').read_bytes()).hexdigest()[:12]
            coach_script=f'<script src="/site-assets/result_coach.js?v={coach_version}" defer></script>'
        return content.replace('</head>', meta + coach_meta + f'<link rel="stylesheet" href="/site-assets/accounts.css?v={css_version}"><link rel="stylesheet" href="/site-assets/ui-polish.css?v={polish_version}"><script src="/site-assets/microphone.js?v={js_version}" defer></script><script src="/site-assets/accounts.js?v={js_version}" defer></script>{coach_script}</head>')

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
        body = f'''<header class="practice-intro"><svg class="brand-wave" viewBox="0 0 100 32" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><path d="M4 14v4m10-9v14m10-19v24m10-16v8m10-18v28m10-21v14m10-11v8m10-16v24m10-18v12m10-8v4"/></svg><p class="eyebrow">Your daily practice</p><h1>Practice English pronunciation.</h1><p>Record a short sentence. Review your words. Find one sound to practice next.</p><div class="practice-limits"><span>General American English</span><span>Up to 5 seconds</span><span>Private recordings</span></div></header><div id="mobile-plan-summary" class="mobile-plan-summary" role="status" hidden></div><div class="practice-layout"><div class="practice-main">
        <details class="account-card guide-card" id="practice-guide"><summary>Explore American sound guides</summary><h2>American sound practice</h2>
        <p id="guide-profile"></p><label for="guide-sentence">Choose a sound guide</label><select id="guide-sentence"></select>
        <div id="guide-target"></div><button id="use-guide" type="button">Practice these words</button>
        <p id="guide-status" role="status"></p></details>
        <section id="recording-workspace" class="account-card recording-workspace" aria-labelledby="practice-heading"><p class="eyebrow">01 / Make a recording</p><h2 id="practice-heading">Record your sentence</h2><details id="practice-settings" class="practice-settings" open><summary id="settings-summary">Lesson settings &middot; Choose a mode</summary><label for="input-mode">Practice mode</label><select id="input-mode"><option value="preset">Preset lesson</option><option value="custom_text">My own sentence</option><option value="free_speech">Free speech</option></select>
        <label id="lesson-label" for="lesson">Practice sentence</label><select id="lesson">{options}</select>
        <label id="custom-label" hidden>My sentence (up to 12 words and 200 characters)<textarea id="custom-text" maxlength="200" rows="3"></textarea></label>
        </details><section class="speaking-exercise" aria-label="Sentence, listening example and recording"><div id="practice-phrase" class="practice-phrase practice-sentence" aria-live="polite"></div><p id="practice-focus" class="practice-focus" hidden></p><details class="listening-example"><summary>Listen to example</summary><p id="lesson-hint"></p><audio id="example" controls></audio><p id="example-label">Synthetic listening example; not used to score your voice.</p></details>
        <div class="record-actions"><button id="record" class="record-button"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/></svg><span>Start recording</span></button><button id="stop" disabled hidden>Stop recording</button></div>
        </section><details class="upload-option"><summary>Upload a WAV instead</summary><label>Up to 5 seconds and 10 MB<input id="recording-file" type="file" accept=".wav,audio/wav"></label></details>
        <div id="mic-meter" hidden><output id="recording-timer" aria-label="Recording time" aria-live="off">0.0 / 5.0 seconds</output><meter id="mic-level" min="0" max="1"></meter><p id="mic-feedback" aria-live="off"></p></div><section id="recording-review" hidden aria-label="Review your recording"><h3>Your recording is ready</h3><p>Listen, then save it or try again.</p><audio id="preview" controls hidden></audio><button id="record-again" type="button">Record again</button><button id="discard-recording" type="button">Discard recording</button><button id="analyze" class="primary" disabled>Check and save my recording</button>
        </section><p id="practice-status" role="status" aria-live="polite">Your recordings and results will appear in My history.</p></section>
        <section id="attempt-result" class="account-card" hidden></section>
        <section id="session-panel" class="account-card" hidden></section>
        <section id="practice-next-card" class="account-card"><h2 id="practice-next-heading">Practice next</h2><div id="suggestions">Set your practice goals in My profile.</div></section>'''
        body += '</div><aside class="practice-sidebar"><section class="account-card plan-card"><p class="eyebrow">A path to follow</p><h2 id="lesson-plan-heading">My lesson plan</h2><div id="lesson-plan" aria-live="polite">Loading your plan...</div></section></aside></div>'
        page = shell('English pronunciation practice', body, '/practice', user)
        return HTMLResponse(page.replace('</head>', '<script src="/site-assets/lesson_plan.js" defer></script></head>'))

    @site.get('/profile')
    def profile_page(request: Request):
        user = current(request)
        if not user:
            return RedirectResponse('/login', status_code=303)
        labels = {'TH': 'think', 'IH': 'ship', 'AE': 'bad'}
        goals = ''.join(f'<label class="profile-goal"><input type="checkbox" name="goal" value="{g}" {"checked" if g in user["goals"] else ""}><span><strong>{g}</strong><span>as in {labels[g]}</span></span></label>' for g in GOALS)
        from practice_guides import PROFILES, profile_guide
        profile_options = ''.join(f'<option value="{key}" {"selected" if user["learner_profile"] == key else ""}>{html.escape(profile_guide(key)["label"])}</option>' for key in PROFILES)
        body = f'''<div class="profile-intro"><p class="eyebrow">Your learning preferences</p><h1>My profile</h1>
        <p>Choose how your name appears and the sounds you want to focus on.</p></div>
        <div class="profile-layout"><section class="account-card profile-card"><header class="profile-header"><p class="eyebrow">Account details</p><h2 id="profile-heading-name">{html.escape(user['display_name'])}</h2>
        <p>Username: <strong>{html.escape(user['username'])}</strong></p></header>
        <form id="profile-form" class="account-form profile-form">
        <fieldset class="profile-group" aria-label="Account details"><label for="display-name">Display name<input id="display-name" name="display_name" value="{html.escape(user['display_name'], quote=True)}" maxlength="60" required autocomplete="nickname" aria-describedby="display-name-help"></label>
        <p id="display-name-help" class="profile-help">1 to 60 characters. This is the name shown when you sign in.</p>
        </fieldset><fieldset class="profile-group"><legend>Practice preferences</legend><div class="profile-accent"><h3>Target accent</h3><p>General American English</p></div>
        <label for="learner-profile">Optional learner guidance<select id="learner-profile">{profile_options}</select></label>
        <details class="profile-guidance-help"><summary>About learner guidance</summary><p class="profile-help">This preference changes practice guidance only. It does not infer your language or change grading. Mandarin-specific calibrated ratings are not enabled.</p></details>
        <fieldset aria-describedby="profile-goals-help"><legend>Sounds I want to practice</legend>
        <div class="profile-goals">{goals}</div></fieldset>
        <p id="profile-goals-help" class="profile-help">Choose sounds to focus on, or leave them unchecked for general practice. These preferences guide suggestions; they are not pronunciation results.</p>
        <p id="profile-selection" class="profile-selection" aria-live="polite"></p>
        </fieldset><div id="profile-actions" class="profile-actions"><button id="profile-save" class="primary" disabled>Save changes</button><button id="profile-discard" type="button" disabled>Discard changes</button></div>
        <p id="profile-status" role="status" aria-live="polite">All changes saved.</p></form></section>'''
        body += '<aside class="profile-plan"><section class="account-card plan-card"><h2 id="lesson-plan-heading">My lesson plan</h2><div id="lesson-plan"></div></section></aside></div><section class="account-card"><h2>Your latest sound checks</h2><div id="profile-progress"></div></section>'
        page = shell('My profile', body, '/profile', user)
        page = page.replace('</head>', '<script src="/site-assets/lesson_plan.js" defer></script><script src="/site-assets/coaching.js" defer></script></head>')
        css_version = hashlib.sha256((ASSETS / 'profile.css').read_bytes()).hexdigest()[:12]
        js_version = hashlib.sha256((ASSETS / 'profile.js').read_bytes()).hexdigest()[:12]
        return HTMLResponse(page.replace('</head>', f'<link rel="stylesheet" href="/site-assets/profile.css?v={css_version}"><script src="/site-assets/profile.js?v={js_version}" defer></script></head>'))

    @site.get('/history')
    def history_page(request: Request):
        user = current(request)
        if not user:
            return RedirectResponse('/login', status_code=303)
        body = '''<h1>My saved attempts</h1><p>Recordings and results stay here when you sign out or restart the app.</p>
        <p>Model feedback is experimental. Changes between attempts do not establish improvement.</p>
        <div class="history-filters"><label>Find a sentence<input id="history-search" type="search" placeholder="Search your saved sentences"></label><label>Status<select id="history-filter"><option value="all">All statuses</option><option value="completed">Completed</option><option value="processing">Processing</option><option value="failed">Failed</option></select></label></div><p id="history-status" role="status"></p><div id="history-list"></div><section id="attempt-result" class="account-card" hidden></section><section id="session-panel" class="account-card" hidden></section>'''
        return HTMLResponse(shell('My history', body, '/history', user))

    @site.get('/api/me')
    def me(request: Request):
        user = require(request)
        return {k: user[k] for k in ('username', 'display_name', 'goals', 'learner_profile')}

    @site.post('/api/profile')
    async def save_profile(request: Request):
        user = require(request)
        csrf(request, request.headers.get('x-csrf-token'), user['csrf'])
        body = await json_body(request)
        try:
            store.profile(user['id'], body.get('display_name'), body.get('goals'), learner_profile=body.get('learner_profile'))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        saved = require(request)
        return {'ok': True, 'profile': {k: saved[k] for k in ('username', 'display_name', 'goals', 'learner_profile')}}

    @site.get('/api/profile/progress')
    def progress_profile(request: Request):
        from accounts.coaching import profile_progress
        return profile_progress(store,require(request)['id'],prompts)

    @site.get('/api/lesson-plan')
    def lesson_plan(request:Request):
        from accounts.lesson_plan import get_plan
        return get_plan(store,require(request)['id'],prompts)

    @site.post('/api/lesson-plan/start')
    async def begin_plan(request:Request):
        from accounts.lesson_plan import start_plan,get_plan
        user=require(request);csrf(request,request.headers.get('x-csrf-token'),user['csrf'])
        options=await json_body(request,allow_empty=True)
        skip=options.get('skip_starting_check',False)
        if type(skip) is not bool:raise HTTPException(422,'Choose whether to skip the starting check.')
        try:start_plan(store,user['id'],prompts,assessment=not skip)
        except ValueError as exc:raise HTTPException(422,str(exc)) from None
        return get_plan(store,user['id'],prompts)

    @site.post('/api/lesson-plan/build')
    async def build_plan(request:Request):
        from accounts.lesson_plan import build_personalized_plan
        user=require(request);csrf(request,request.headers.get('x-csrf-token'),user['csrf'])
        try:return build_personalized_plan(store,user['id'],prompts)
        except ValueError as exc:raise HTTPException(422,str(exc)) from None

    @site.post('/api/lesson-plan/skip')
    async def skip_check(request:Request):
        from accounts.lesson_plan import get_plan,start_plan
        user=require(request);csrf(request,request.headers.get('x-csrf-token'),user['csrf'])
        plan=get_plan(store,user['id'],prompts)
        if plan['kind']=='assessment':
            try:
                start_plan(store,user['id'],prompts,restart=plan['started'],assessment=False,expected_plan_id=plan['plan_id'])
            except ValueError as exc:raise HTTPException(422,str(exc)) from None
        return get_plan(store,user['id'],prompts)

    @site.post('/api/lesson-plan/restart')
    async def restart_plan(request:Request):
        from accounts.lesson_plan import start_plan,get_plan
        user=require(request);csrf(request,request.headers.get('x-csrf-token'),user['csrf'])
        if (await json_body(request)).get('restart') is not True:raise HTTPException(422,'Confirm starting a new plan.')
        try:start_plan(store,user['id'],prompts,restart=True,assessment=False)
        except ValueError as exc:raise HTTPException(422,str(exc)) from None
        return get_plan(store,user['id'],prompts)

    @site.get('/api/lessons')
    def lessons(request: Request):
        require(request)
        return [{'id': p['id'], 'text': p['text'], 'hint': p.get('practice_tip', ''), 'target_words':p.get('target_words',[]), 'target_phones':p.get('target_phones',[])} for p in prompts]

    @site.get('/api/suggestions')
    def suggestions(request: Request):
        user = require(request)
        return {'phones': store.suggestions(user['id'], user['goals'])}

    @site.get('/api/practice-guides')
    def guides(request: Request):
        user = require(request)
        from practice_guides import practice_guides
        from voice_generation.runtime import generation_capabilities
        return dict(practice_guides(user['learner_profile']), generation=generation_capabilities())

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

    @site.post('/api/attempts/{identity}/coaching')
    async def explain_result(request:Request,identity:str):
        from ai_coaching.contract import CoachingRequest
        from pydantic import ValidationError
        timeout=min(max(coaching.config.timeout,0.1),5)
        if not 0.1<=timeout<=5:timeout=5
        try:
            # Include authentication and request decoding in the optional deadline.
            async with asyncio.timeout(timeout):
                user=await asyncio.to_thread(require,request)
                csrf(request,request.headers.get('x-csrf-token'),user['csrf'])
                try:options=CoachingRequest.model_validate(await json_body(request))
                except ValidationError:raise HTTPException(422,'Invalid explanation request.') from None
                return await coaching.explain(request.cookies.get(COOKIE),identity,**options.model_dump())
        except TimeoutError:return dict(status='unavailable',code='timeout')
        except PermissionError:raise HTTPException(404,'Attempt not found.') from None

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
