# Optional neural listening examples

The main application defaults to Parthiban's Windows System.Speech backend. That default callable and the pronunciation-analysis worker are unchanged. Kokoro produces a synthetic example, not a conversion of the learner's voice and not a scoring reference.

## What is implemented

`voice_generation/runtime.py` connects the existing authorized generation job to a lazy, reusable subprocess launched with a separately configured Python interpreter. `voice_generation/external_worker.py` runs Parthiban's existing Kokoro backend inside that environment. No Torch, spaCy or Kokoro model is imported into the web process by this adapter. Requests enforce 12 words/200 characters, use private JSON stdin/stdout, validate generated IDs and readable WAV output, and have a 120-second generation deadline. Timeout/failure retires only the owned process tree and removes newly created partial outputs. Generation failure leaves analysis intact.

The subprocess is local and runs offline. It uses `models/kokoro/manifest.json`, `config.json`, `kokoro-v1_0.pth` and `voices/af_heart.pt`; the backend also needs its English spaCy package. There is no setup or download during an assessment. The current laptop does not have this separate environment or these assets, so real neural generation is not yet verified here. Transport/backend-reuse/failure tests use controlled doubles.

## Explicit setup and activation

Use a dedicated environment compatible with the existing pinned generation dependency files. Do not install them into `.venv`, which runs assessment. Follow Parthiban's `voice_generation/KOKORO_RUNBOOK.md` for dependency installation, spaCy setup, pinned model manifest and listening review. Those installation/download steps were not executed as part of this integration.

After that environment and assets have been tested, set these variables in the PowerShell window used to launch the app:

```powershell
$env:ACCENT_COACH_EXAMPLE_BACKEND = 'kokoro'
$env:ACCENT_COACH_KOKORO_PYTHON = (Resolve-Path '.\voice_generation\.venv\Scripts\python.exe').Path
.\.venv\Scripts\python.exe app_2.py
```

Only a trusted local operator sets the executable; it is not an HTTP parameter. The web app still uses the shared assessment environment. In Practice, review/confirm text, then request a synthetic example. First generation includes loading the separate model; subsequent requests reuse it. Review its spoken words and pronunciation before a demo. Do not label it voice-preserving conversion.

## Speed and fallback

Keep Kokoro disabled for the current speed demonstration until its memory and latency have been measured on this laptop. Analysis and generation deliberately retain the existing bounded serial scheduler; a generation job can queue analysis, and a retained neural model can add RAM pressure. Process separation prevents package/thread-setting changes in assessment, but does not guarantee the absence of CPU or memory contention.

To use the proven desktop backend again, stop the app normally, set the following in its launch window and restart:

```powershell
$env:ACCENT_COACH_EXAMPLE_BACKEND = 'windows'
Remove-Item Env:ACCENT_COACH_KOKORO_PYTHON -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe app_2.py
```

Do not launch a second app on an occupied port. No shared model, MFA, timeout, cache or analysis setting needs to change for this fallback. Backend failure is shown explicitly; the adapter does not silently substitute a different voice.
