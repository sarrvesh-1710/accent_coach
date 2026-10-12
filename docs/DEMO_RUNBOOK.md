# Local demo setup and rehearsal

## Reproduce the environment

Use Python 3.13 on Windows (the tested laptop version). In the repository folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-scoring.txt
.\.venv\Scripts\python.exe tools/setup_models.py
```

The model setup downloads public, pinned model files. It does not upload recordings. Inference in the beginner app is offline and uses the cache. Do not rely on a first-use model download during the presentation.

MFA runs in its own Conda environment. On the tested laptop this is MFA 3.3.7:

```powershell
conda create -n accent-coach-mfa -c conda-forge montreal-forced-aligner=3.3.7
conda run -n accent-coach-mfa mfa model download dictionary english_us_arpa
conda run -n accent-coach-mfa mfa model download acoustic english_us_arpa
```

Configure the machine-specific Conda command in ignored `phoneme_scoring/settings.local.json`, replacing the example path:

```json
{"mfa":{"command":["C:/path/to/conda.exe","run","--no-capture-output","-n","accent-coach-mfa","mfa"]}}
```

Verify setup:

```powershell
.\.venv\Scripts\python.exe tools/check_installation.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe phoneme_scoring/gop_score.py --self-test
.\.venv\Scripts\python.exe app_2.py
```

Open http://127.0.0.1:7861/. If this port is occupied, check whether the app is already open. Use `GRADIO_SERVER_PORT` to deliberately select another port. Do not stop unrelated processes.

## Current limits

- 12 preset English lessons, 1–12 words in configuration, recording maximum five seconds.
- Target contrasts TH versus S/T/F, IH versus IY, and AE versus EH. Other displayed sounds are practice hints.
- No reference waveform required. No whole-sentence correctness grade or accent score.
- Upload cap: 10 MB. Backend rejects inputs over 8 channels or 192 kHz in addition to format, duration, silence, and sample checks.
- One active analysis worker; queue holds at most eight waiting requests. Concurrent direct worker calls are rejected. The UI permits recording again after completion/failure.
- Main app worker deadline: 180 seconds plus process cleanup. MFA timeout: 120 seconds. A timed-out worker and its Windows child processes are terminated; the next attempt starts a fresh worker. A killed attempt may leave a partial run folder without results.json, which history intentionally excludes.
- The worker reuses loaded models between successful attempts. Stage timings are recorded in completed results.
- App instances share an operating-system lock at `%USERPROFILE%/.accent_coach/mfa.lock` before starting MFA. This prevents simultaneous extraction into MFA's shared acoustic-model cache. The lock releases when its owning process exits; do not delete it to bypass a running alignment. External MFA commands that do not use this app's lock should not run concurrently with the demo.

## Rehearsal checklist

1. Open every sentence in the dropdown. Confirm the words, target, and written hint correspond.
2. Record a normal example for each contrast; inspect recognized words and target outcome.
3. Record a deliberate target change (sink/fink, sheep, bed); have a teammate confirm what was actually said.
4. Try a different sentence, silence, clipping, and a recording longer than five seconds. Confirm recovery guidance and no positive judgment for a known unusable input.
5. Replay the result, select Record again, and change the lesson. Confirm old results are cleared.
6. Open My saved attempts, refresh, select a completed attempt, and replay it. Delete only a disposable practice attempt using the explicit confirmation box. Confirm it disappears after refresh.
7. Rehearse from a cold app start and repeat once to observe warm processing time. Test with networking disconnected after setup; linked external lessons will be unavailable offline.
8. Keep consented demo clips and screenshots available if live microphone capture fails.

## Freeze the tested build

```powershell
.\.venv\Scripts\python.exe tools/release_snapshot.py
```

`runs/demo_release.json` records the Git base, exact source hashes (including uncommitted files), Python/dependency versions, and model settings. This is a reproducibility record, not a substitute for committing the reviewed changes. Keep reports with the exact code version your team presents. Raw learner recordings and runs remain ignored by Git.

## Public deployment is a separate release

The app binds to 127.0.0.1 with sharing disabled. **Do not expose this local build publicly:** its history is shared by the person using the laptop, not separated into authenticated accounts. This work did not publish a site or select paid hosting.

Before hosting for multiple users, implement authentication and per-user ownership for recording routes/history/deletion; remove directory-wide file access; use HTTPS; enforce rate limits and request timeouts at the server; test upload validation before decoding; monitor CPU, memory, queue limits, and errors; define retention/consent; and verify backups and deletion. Choose the destination and expected concurrent users before sizing it. Gradio's local upload cap and queue are only part of that work.

## Recording storage and deletion

Saved attempt folders under `runs/` contain learner audio, analysis copies, transcript/alignment artifacts, and result JSON. They remain until explicitly deleted. The history deletion button removes the selected completed folder after confirmation. Active/incomplete folders are not offered for deletion. Symlinks and Windows junctions are refused by the storage layer.

Gradio may cache uploads/playback copies separately. Its configured cleanup runs hourly and expires copies older than 24 hours while the app is running. Deleting a saved attempt does not promise immediate removal of browser-held or cached copies; refresh/close old pages and apply the retention process when handling recordings. History has no automatic improvement score.
