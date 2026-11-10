# demo-1: current laptop application and Azure handoff

Owner/integration coordinator: Sarrvesh. Snapshot date: November 10, 2026. Branch: **demo-1**. Repository: https://github.com/sarrvesh-1710/accent_coach.

This branch packages the current laptop application, not an older teammate feature branch. It includes all current application modules/assets, recording UI, transcript confirmation, private profiles and lesson plans, Practice results, original playback and History, reliability safeguards, existing MFA resource/process reuse, optional synthesis adapters and optional AI-coaching code. Publishing Git source does not deploy the website or share accounts.

## 1. Get this exact branch

Use a new clone to preserve your own work:

```powershell
git clone --branch demo-1 --single-branch https://github.com/sarrvesh-1710/accent_coach.git accent-coach-demo-1
cd accent-coach-demo-1
git branch --show-current
git rev-parse HEAD
git status --short
```

Expected branch: `demo-1`. Compare HEAD with the commit linked in Sarrvesh's handoff. The new clone should have a clean working tree. For a clean existing checkout already on `demo-1`, use `git pull --ff-only origin demo-1`. If you are on another branch, have local changes or have diverged, use the separate clone; do not reset or overwrite teammate work.

Git includes source, tests, public synthetic example assets and setup documentation. It deliberately excludes `.venv`, downloaded models, `settings.local.json`, private databases/accounts, human recordings, result folders, screenshots/previews, API keys and machine caches. **Create your own account. Sarrvesh's login and History are not copied.**

## 2. Recreate the Windows app environment

The tested laptop runtime is Windows x64/Python 3.13. MFA is a separate Conda environment with Python 3.11 and MFA 3.3.7. Install those prerequisites and Node.js for the JavaScript tests using their official installers. Do not install optional voice experiments into the assessment environment.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-demo-1.txt
```

`requirements-demo-1.txt` records the actual installed direct-package versions used on the laptop. Older account declarations specify newer FastAPI/Uvicorn versions; the demo file intentionally records tested FastAPI 0.141.1 and Uvicorn 0.53.0. No dependency was upgraded for publication. This snapshot is not a universal Linux lock or proof that a fresh dependency installation has succeeded on your machine. If installation fails, preserve the exact error and stop rather than substituting untested versions silently.

Download the shared, revision-pinned ASR and phoneme model weights explicitly:

```powershell
.\.venv\Scripts\python.exe tools/setup_models.py
```

This setup downloads public models; it does not upload recordings. The app subsequently expects local cached weights in `models/huggingface`. Both model IDs/revisions remain in `phoneme_scoring/settings.json`. Their presence alone does not prove inference works.

## 3. Install MFA and recreate the same opt-in fast path

In an Anaconda/Conda-enabled PowerShell:

```powershell
conda create -n accent-coach-mfa --override-channels -c conda-forge python=3.11 montreal-forced-aligner=3.3.7 -y
conda run -n accent-coach-mfa mfa model download dictionary english_us_arpa
conda run -n accent-coach-mfa mfa model download acoustic english_us_arpa
conda activate accent-coach-mfa
.\.venv\Scripts\python.exe tools/configure_demo_mfa.py --prefix "$env:CONDA_PREFIX"
conda deactivate
```

The helper creates **your** ignored `phoneme_scoring/settings.local.json`, with a direct MFA executable, child native-library paths, writable dictionary cache, `reuse_process: true`, `idle_sec: 600` and `reuse_lexicon_graphs: true`. It checks the same MFA 3.3.7 runtime gate as the app. It neither changes shared model/analysis settings nor runs/downloads a model. It refuses to overwrite existing local settings. On an already configured installation, retain and review those settings rather than replacing them. Never copy Sarrvesh's absolute executable/PATH values.

Named MFA resources normally use `$HOME/Documents/MFA`; if you use `MFA_ROOT_DIR`, set it consistently for both downloads and the app. `transcript_input.py` must find the same actual dictionary used by MFA. `DEMO_1_RUNTIME_SNAPSHOT.json` records the laptop resource hashes for comparison; named-resource downloads may change and a hash mismatch requires investigation.

Process/graph reuse is gated to a direct Windows MFA 3.3.7 runtime. Unsupported configurations fall back to the ordinary CLI. Each recording still gets fresh alignment and isolated temporary paths; learner results are not cached to make new recordings appear faster. Existing locks, deadlines, identity and revision checks remain enabled. Warm models/resources must be prepared and measured on the new machine; **no ten-second guarantee is transferred by Git**.

## 4. Launch and verify locally on that machine

From the repository folder:

```powershell
.\.venv\Scripts\python.exe app_2.py
```

Open http://127.0.0.1:7861/ on the computer running it. Keep that terminal open. If the port is already occupied, use the running app or deliberately select a different `GRADIO_SERVER_PORT`; do not launch competing copies. Use `ACCENT_COACH_OPEN_BROWSER=0` on a VM when automatic browser opening is unnecessary.

Create a new account, choose a preset or Free speech, and submit an original human recording under **5 seconds/10 MB**. Custom/confirmed text is limited to **12 words/200 characters**. Review the recognized text, explicitly confirm it and analyze. Verify:

- Result visible in Practice, original recording playable, and the same attempt reopens from private History after refresh/restart.
- Selected, recognized and confirmed words remain distinct. Editing/replacing input invalidates old current results.
- Processing completion is not a pronunciation pass. Unsupported/uncertain results are inconclusive, not errors.
- Separate listening examples remain labeled synthetic and are never submitted as learner evidence.
- First-use setup, transcription, analysis, warm repeats, failures and user/network wait are measured separately. Do not present retries of the same clip as fresh-recording speed.

Run regressions:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
node --test tests/session_playback.cjs
node --test tests/profile_rendering.cjs
git diff --check
```

Most speech/provider unit tests use doubles or synthetic inputs. They do not prove model accuracy, human usefulness or new-machine speed. Node wrappers can skip JavaScript tests if Node is absent. Separately perform one real recording-to-feedback check. Optional `tools/check_installation.py` writes an ignored readiness report and runs an MFA version command; its direct-MFA version check does not apply `mfa.environment`, so run it in an activated MFA environment or account for that known checker limitation.

## 5. Optional generation and AI coaching

Windows desktop speech is the default synthetic-example backend; it depends on an installed compatible Windows voice. Static public lesson examples are included. Kokoro remains optional, needs a separate runtime/models, and is documented in `OPTIONAL_KOKORO_SETUP.md`. Do not enable it until its memory use, quality and latency have been tested independently.

Optional **Explain this result** stays disabled unless a compatible runtime provider/model is configured. No paid API service is required for the base app. See `OPTIONAL_AI_COACHING.md` for server-side variables, the external-provider consent choice and the five-second optional deadline. Do not put credentials into Git, browser code or chat. Coaching never receives audio or changes analysis categories/progress. Live provider compatibility/latency remains unverified.

## 6. Azure: what is and is not ready

For the closest reproduction, start with a **Windows x64 VM** and the environment above. Linux is not a verified equivalent: the default desktop synthesis and the current persistent-MFA runtime gate are Windows-specific. A Linux port needs separately verified synthesis/runtime handling and performance tests. Do not turn off guards to force a fast path.

This snapshot intentionally retains the laptop's network behavior:

- `site_server.py` binds to `127.0.0.1:7861`.
- `accounts/web.py` allows localhost/loopback Host headers and checks same-origin CSRF.
- `private_data` is local to that installation; accounts/history are not synchronized through Git.
- Public domain/policy settings remain unset/unreviewed. The Privacy page currently describes a local prototype plus optional text coaching.

**Opening an Azure port alone does not turn this snapshot into a public website.** For an initial engineering test, run the browser inside the VM through authorized remote desktop. If the VM has separately configured, authorized SSH access, a tunnel can preserve loopback-only behavior:

```powershell
ssh -N -L 8786:127.0.0.1:7861 YOUR_VM_USER@YOUR_VM_ADDRESS
```

Then open http://127.0.0.1:8786/ on the tunnel client while the app is running on the VM. Windows SSH access is not assumed installed/configured by this repository. Use a separate browser profile if simultaneously using a local app with the same localhost cookie name; cookies are not isolated by port.

Before public exposure, coordinate an explicit deployment change through Sarrvesh: reviewed HTTPS/reverse-proxy and trusted-host/origin/cookie configuration, persistent private data location, restricted storage/backups, accurate cloud-processing privacy text and real two-account authorization/browser tests. A domain/proxy configuration must be validated; do not weaken CSRF or remove ownership checks. The user has authorized publishing this branch, not an unreviewed public deployment.

On Azure, benchmark the same source/model/settings and at least three comparable recordings. Retain cold/warm/retry and failure runs. VM size, memory pressure, native runtime and network overhead can change results. Keep models loaded for the demo, but report preparation separately. AI coaching and synthesis must remain separate opt-in actions.

## 7. Handoff checklist

- [ ] Clone `demo-1` and verify the published commit.
- [ ] Install app dependencies; download pinned models and MFA resources.
- [ ] Create machine-local MFA settings; preserve the existing safety gates/reuse code.
- [ ] Run tests and a real short-recording workflow.
- [ ] Verify original playback, private History, transcript edits and two-account isolation.
- [ ] Record new-machine timings; do not inherit old speed claims.
- [ ] Review deployment configuration and cloud privacy before public access.
- [ ] Keep optional AI/Kokoro disabled until explicitly configured/tested.

Report the commit, OS/VM size, package versions, exact failures and measured cold/warm stage times back to the team. Never send passwords, API keys, private database files or unconsented recordings in Git.
