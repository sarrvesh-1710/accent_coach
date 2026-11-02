# Accent Coach: teammate setup and walkthrough

Current integration branch: `feature/speed-free-speech`. Date: November 2, 2026. This guide supersedes older setup/workflow descriptions where they conflict. Historical test and timing reports remain dated evidence, not promises about every machine.

## 1. Get the integrated code safely

Recommended: use a separate clone so your own branch, uncommitted changes and local environment remain intact. Run from a parent folder that does not already contain `accent_coach-integrated`:

```powershell
git clone --branch feature/speed-free-speech --single-branch https://github.com/sarrvesh-1710/accent_coach.git accent_coach-integrated
cd accent_coach-integrated
git status --short
git log -3 --oneline
```

For an existing checkout already on this branch with a clean working tree, use `git fetch origin` followed by `git pull --ff-only origin feature/speed-free-speech`. If it is dirty, on your own feature branch or diverged, preserve it and use the separate clone. Do not reset it or copy older account/UI files over the integrated version.

A Git clone includes code, tests and reports. It does not include our installed environments, local accounts, learner recordings, model weights, compiled dictionary caches or machine-specific settings. Your local account is created on your own installation; Sarrvesh's credentials/history are not shared through Git.

## 2. Prepare a Windows installation

An existing working installation can keep its compatible environment and local settings. New-install commands below are setup instructions, not claims that installation was performed on your computer. The latest inspected application used Python 3.13; MFA uses a separate Python 3.11 Conda environment. Keep Kokoro separate.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-scoring.txt -r requirements-accounts.txt
conda create -n accent-coach-mfa --override-channels -c conda-forge python=3.11 montreal-forced-aligner=3.3.7 -y
conda run -n accent-coach-mfa mfa model download dictionary english_us_arpa
conda run -n accent-coach-mfa mfa model download acoustic english_us_arpa
.\.venv\Scripts\python.exe tools/setup_models.py
```

Internet is required for explicit setup/downloads. Assessment uses the pinned local models offline. Use the repository's declared versions and do not upgrade the working assessment environment to install a generation experiment. See the existing README MFA setup section for the ordinary Conda command adapter, and `docs/ACCOUNTS_SETUP.md` for local account/storage details. The latter's original preset-only limitation is historical; custom and free speech are now integrated.

Reproducibility caveat: the November 2 regression run used installed FastAPI 0.141.1 and Uvicorn 0.53.0, while the existing account requirements declare 0.143.0 and 0.54.0. `pip check` passed for the installed environment. This publication did not upgrade packages or verify a clean installation of those newer declarations. Record your actual versions and run the tests on your machine; do not describe the declared environment as freshly validated here.

Configure **your own** ignored `phoneme_scoring/settings.local.json`. The shared `settings.json` pins model IDs/revisions and CPU settings. Relative Hugging Face cache paths resolve from that settings directory, so the default is the repository's `models/huggingface`.

The inspected fast path needs all of the following:

| Local setting | Meaning |
| --- | --- |
| `mfa.command` | A one-element array containing the absolute path to your MFA 3.3.7 `Scripts/mfa.exe`. The multi-element `conda run ... mfa` adapter works as the ordinary CLI path but does not enable interpreter reuse. |
| `mfa.environment` | Child environment overrides providing your MFA environment's `CONDA_PREFIX` and a `PATH` with that prefix, `Scripts`, `Library/bin`, and normal system paths. Resolve these on your computer; do not copy Sarrvesh's personal paths. |
| `mfa.dictionary_cache_directory` | An absolute writable local directory, normally inside your ignored `runs/mfa_dictionary_resources`. |
| `mfa_execution` | The optional resource/process reuse flags shown below. |

Merge this **fragment** into the existing local settings without replacing your model/MFA paths:

```json
"mfa_execution": {
  "reuse_process": true,
  "idle_sec": 600,
  "reuse_lexicon_graphs": true
}
```

Reuse is gated to the inspected direct Windows MFA 3.3.7 runtime. Unsupported runtimes retain the ordinary CLI fallback; no latency guarantee applies. Each request still aligns its own recording/text. The caches contain dictionary resources, not learner results. Set graph reuse false to use original graph loaders, or process reuse false to use ordinary CLI execution. Restart normally after changing Python code; do not start a second server on an occupied port. Do not enable profiling/diagnostic capture for an ordinary demo.

The existing `tools/check_installation.py` checks packages/cached models and attempts an MFA version command. It writes an ignored setup report and is not a real analysis acceptance test. Its MFA subprocess does not apply the local `mfa.environment` overrides, so a direct-MFA check may fail from a shell lacking the Conda native paths even when the app's configured child environment works. Verify that condition rather than replacing working settings to force a checker pass.

## 3. Start and use the site

```powershell
.\.venv\Scripts\python.exe app_2.py
```

Open `http://127.0.0.1:7861/`. Create your own account using the form, or sign in to an existing local account. Passwords belong only in the app. If the port is occupied, check the already running site instead of launching another copy.

1. In My profile, choose the sounds you want to practice. Save and Discard show whether changes are pending. Optional Mandarin-speaking learner guidance changes educational guidance only; the assessment target remains General American English.
2. Choose a preset, My own sentence, or Free speech. The American sound guides can fill the custom-text practice flow; they are teaching material, not detected mistakes.
3. Record or upload your original learner WAV: no more than five seconds and 10 MB. Custom/confirmed text allows up to 12 words and 200 characters. A synthetic example must never be uploaded as learner test evidence.
4. For custom/free speech, save and transcribe, inspect the recognized text, correct it if needed, then explicitly confirm. Recognized text remains separate from your correction.
5. Analyze confirmed words. Watch the real processing indicator. Results appear in Practice and remain in private History. Preset mode runs the existing preset content-check path.
6. Replay the original recording, inspect Processing times, use Start new practice, or View in History. Open the saved attempt to verify persistence. Text/recording changes invalidate prior current results; failed jobs expose a retry/error state.
7. Request Hear a synthetic example separately after confirmation. Desktop Windows speech is the current default. A generated example is labeled separately and is never used as the scoring reference.

No cloud speech API key or external login provider is required for the default local workflow. Optional `ACCENT_COACH_DATA_DIR` relocates private local storage, `GRADIO_SERVER_PORT` changes the local port, and `ACCENT_COACH_OPEN_BROWSER=0` suppresses automatic browser opening. Keep private directories out of source control.

## 4. Explain it to a sponsor

**Sarrvesh:** "My part takes a short recording, recognizes the words, and lets the learner correct them before analysis. It matches those confirmed words to the original recording and gives experimental feedback on supported sounds. I also profiled the slow alignment stage and added reusable dictionary resources and an initialized process while keeping recording and revision checks. Earlier prepared tests were often below ten seconds, but the latest laptop runs are slower, so reliable speed remains an open issue."

**Lucas:** "The account system keeps each learner's recordings and results in private History, so they can return and replay their practice. Profile preferences guide the sounds suggested for practice. The integrated American guides and optional Mandarin learner preference provide learning guidance; they do not establish a trained accent grade."

**Parthiban:** "The learner can request a separately labeled synthetic listening example for the confirmed words. Desktop synthesis is the working baseline, while the optional Kokoro adapter runs in its own environment when configured. The integrated profile controls and status messages make saving and reviewing clearer. Synthetic examples are not the learner's converted voice; voice-preserving conversion remains experimental work outside the working baseline."

These explain the integrated responsibilities and include selectively adapted teammate contributions. See `TEAM_FEATURE_INTEGRATION_2026-10-28.md` and `DEMO_POLISH_2026-11-01.md` for source-branch attribution and verification.

## 5. Explain outputs honestly

| Output | Meaning |
| --- | --- |
| Recognized words | What the recognizer produced; it can be mistaken. |
| Confirmed text | The learner's explicitly accepted words used for alignment. |
| Supported | The model favored the expected sound over tested alternatives. |
| Practice | A tested alternative was favored; a possible place to practice, not a confirmed error. |
| Inconclusive | Evidence, dictionary coverage or supported-sound coverage is insufficient. |
| Completed | The processing job finished; it does not mean pronunciation is correct. |
| Processing times | Saved measured job times, with transcription and analysis separated. |

The eligible contrasts remain TH versus S/T/F, IH versus IY, and AE versus EH in supported contexts. There is no validated whole-accent percentage, universal sound coverage or calibrated overall grade. Precise per-occurrence coaching/playback beyond the current output is proposed future work, not an implemented feature.

## 6. Speed and demo limits

Read `SPEED_INCIDENT_2026-11-02.md` before promising latency. On November 2 initial free-speech transcription took 93.00 seconds and its analysis 41.05 seconds. A later preset took 32.54 seconds before saving with proven process/dictionary/graph reuse. Low available RAM and paging were observed; a controlled root-cause and recovery comparison is unfinished.

The historical prepared-analysis median of 8.19 seconds was real but conditional, with an outlier above ten seconds. It excluded the separate transcription step. Startup, idle process exit, memory pressure, generation jobs and CPU/background work can change wait times. A ten-second maximum and a ten-second complete workflow are not verified.

Before a demo, run one complete practice, record its actual timings, keep startup separate, avoid concurrent jobs and leave the app running. This preparation is not proof that the next clip meets the target. If analysis is slow or fails, show its real state and use a clearly identified older saved result to explain the output. Do not pass a saved result off as a fresh assessment.

Kokoro is opt-in and was not installed or real-model verified on this laptop. See `OPTIONAL_KOKORO_SETUP.md`. Keep desktop speech as the baseline until separate model quality, latency and RAM checks pass. The shared serial queue means generation can delay analysis even though models are process-isolated.

## 7. Verify and coordinate changes

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/session_playback.cjs
node --test tests/profile_rendering.cjs
git diff --check
```

Node.js is needed for the production-JS rendering scenarios; Python wrappers skip them if Node is missing. Unit/mocked subprocess tests do not establish human pronunciation accuracy or actual model latency. Historical real-model/browser evidence and incomplete fresh-human acceptance cases are identified in the dated reports. Do not count every JS scenario as an additional Python test.

Coordinate shared `app_2.py`, `pipeline.py`, `accounts/web.py` and `web_assets/accounts.js` changes through Sarrvesh. Lucas reviews account ownership/storage/History changes; Parthiban reviews generation/runtime changes. Preserve the current worker/cache files and local settings when integrating UI changes. Test identity/revisions, generated-versus-learner separation, limits, original playback and analysis persistence before proposing a merge.

Use a new branch from this reviewed integration state for follow-up work, push that branch and request review. Do not merge an older combined teammate branch wholesale over the current speed build. The application remains localhost-only; publishing code to GitHub does not deploy a shared public website or synchronize private accounts.
