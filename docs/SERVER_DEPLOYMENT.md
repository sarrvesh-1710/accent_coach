# Server deployment handoff

Branch: `profile-system`. No server has been deployed by this change. The normal
local demo remains `powershell -ExecutionPolicy Bypass -File .\start_demo.ps1 -Demo`.

The same FastAPI site can run behind an HTTPS reverse proxy on an external server.
Frontend requests use same-origin paths, so accounts, profiles, history and audio
routes move together without hardcoded localhost API URLs. Run the app at the
root of one domain. A separate-origin frontend or a subpath mount is additional
integration work; no broad CORS policy was introduced.

## Configuration supplied by the operator

Copy and edit `deploy/hosted.env.example`. `site_server.py` reads process environment
variables; it does not automatically load an .env file. The provided systemd
example loads `/etc/accent-coach.env`; managed platforms can supply these variables
through their environment settings.

- `ACCENT_COACH_MODE=hosted`: HTTPS redirects and Secure authentication cookies;
  rejects sample demo mode and incomplete hosting configuration.
- `ACCENT_COACH_PUBLIC_URL`: canonical HTTPS origin, e.g. https://coach.example.com.
- `ACCENT_COACH_ALLOWED_HOSTS`: exact hostnames, comma separated, no schemes,
  ports or wildcard. Requests to other hostnames are rejected.
- `ACCENT_COACH_DATA_DIR`: absolute path to a persistent private directory outside
  the web root. The service account needs read/write access. Do not use an ephemeral
  container layer or serve this directory as static files.
- `ACCENT_COACH_HOST`: default 127.0.0.1 for a reverse proxy on the same machine.
  A container platform may require 0.0.0.0 inside its private container network.
- `PORT`: hosting listen port. Local demo GRADIO_SERVER_PORT still works.
- `FORWARDED_ALLOW_IPS`: actual trusted proxy IPs or bounded networks. The app only
  trusts forwarded HTTPS/client information from those peers. Never set `*`.
- `ACCENT_COACH_KOKORO_PYTHON`: path to the separate generation interpreter;
  Windows and POSIX environment layouts are supported by the existing bridge.
- `ACCENT_COACH_GENERATION_BACKEND=kokoro`: Windows desktop TTS is not a Linux
  server fallback. `ACCENT_COACH_OPEN_BROWSER=0` is appropriate for services.

Start from the repository root using the main environment:

```sh
/opt/accent-coach/.venv/bin/python site_server.py
```

The launcher fixes Uvicorn to one app worker and passes the explicit proxy trust
settings. Configure one service/replica per data directory. Do not run the sample
`run_profile_demo.py` on the real hosted data volume.

## Runtime and model setup

1. Install Python 3.12, create the main environment, and install requirements.txt,
   requirements-accounts.txt and requirements-scoring.txt. Test the declared pins
   on the server OS rather than copying a Windows .venv to Linux.
2. Create the separate Kokoro environment using voice_generation/KOKORO_RUNBOOK.md,
   including its spaCy model and pinned weights under models/kokoro. Configure its
   interpreter path. The bridge does not import Kokoro into the main environment.
3. Install MFA and its dictionary/acoustic model in its own supported environment.
   Download Whisper and phoneme checkpoints through the existing setup tools.
   Configure server paths in ignored phoneme_scoring/settings.local.json. Do not
   copy the laptop's absolute Windows paths to Linux. For example, MFA's command
   can use the server's `conda run --no-capture-output -p /path/to/mfa-env mfa`.
4. Run the model setup as the service identity or grant it appropriate access to
   model caches/MFA cache/home and temporary directories. The current laptop still
   references older checkout assets; those paths must be replaced on the server.
   Inference should use already-installed local weights, not first-user downloads.
5. Configure the domain and HTTPS certificate/reverse proxy. Adapt
   deploy/nginx.conf.example to the actual certificate paths and hostname.
   It preserves Host and replaces forwarded headers, bounds upload size, and
   forwards to the local app port. Microphone capture needs HTTPS in browsers.
6. If using Linux/systemd, adapt deploy/accent-coach.service.example to the actual
   install path, service user and environment file. Templates are not installed
   or enabled automatically by this repository.

## Moving existing profiles

Stop the source app before copying the complete private data directory, or make a
consistent SQLite backup. Preserve recordings/results, not only the users table.
Transfer that backup privately using the team's chosen secure method, restore it
into the persistent server directory, set ownership/permissions for the service
identity, and point ACCENT_COACH_DATA_DIR there. Source recordings and account data
are intentionally ignored by Git and are not in the source ZIP.

Take and test backups according to the hosting environment. SQLite WAL files need
consistent handling; copying a live main .sqlite3 file alone is insufficient.
On the new domain, users sign in using their existing credentials; browser cookies
from localhost do not transfer automatically. Confirm saved language, sound goals,
history, playback, deletion and a new recording before switching users over.

## Single-instance limits

This build supports a single persistent app instance. Analysis queues, cached
models and generation workers are in process. Startup recovers interrupted jobs
and cleans private temporary work. Multiple workers/replicas sharing the same data
could interfere with each other's jobs, so stop the old instance before starting
its replacement. Do not use auto-reload for the hosted service.

A hosted platform with ephemeral disk or forced horizontal scaling needs a durable
job queue, shared/object storage and database/recovery changes first. The current
SQLite layout can serve a small single-server deployment; it is not a tested
multi-instance architecture. Hardware capacity and real concurrent-use limits need
measurement on the chosen server. No public load test or Linux model execution
has been claimed by this change.

## Verification before switching the domain

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python tools/check_combined_demo.py
```

Run those checks on the server after runtime/model setup. The combined smoke uses
temporary accounts and synthetic audio; it exercises real installed speech and
Kokoro engines but does not establish human pronunciation accuracy. Check the real
HTTPS domain in a browser for signup/login, Secure cookies, profile save/reload,
microphone permission, analysis, history, private playback and sign-out. Test two
users and an application restart. `/site-health` checks the web process, not model
readiness; its `public_launch: false` is not a deployment certification.

The repo's site_config.json still records that public-facing policies are not
reviewed. Review the actual hosted privacy/retention/contact terms before a public
launch. This change configures portability; it does not expose localhost, install
certificates or upload any user data to a server.

## Official configuration references

- https://uvicorn.dev/settings/ (listen port, proxy headers and forwarded peers)
- https://fastapi.tiangolo.com/deployment/https/ (HTTPS termination proxy behavior)
- https://www.starlette.io/middleware/ (trusted hosts and HTTPS redirects)

## Verification recorded for this change

The full suite ran 186 tests: 185 passed, one existing Windows symlink skip.
Five hosted-configuration tests cover explicit settings, HTTPS signup/login and
Secure cookies, persistent profile updates and restart, CSRF, rejected hosts,
HTTP redirection, and trusted/untrusted proxy behavior. These are application/ASGI
checks on the development laptop, not an installed Nginx, real-certificate, public
load, or Linux speech-runtime test. The local browser/demo defaults are retained.
