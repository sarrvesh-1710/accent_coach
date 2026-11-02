# Publication verification: November 2, 2026

## Scope and baseline

The project lead explicitly requested committing/pushing the accumulated work and providing instructions for teammates. Starting branch: `feature/speed-free-speech`; starting HEAD and origin branch: `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`. The index started empty. Existing playback, MFA resource/worker speed changes, reliability fixes, Practice results and selectively adapted team features were present as unstaged/untracked source and were preserved.

This publication adds setup/handoff documentation and a README entry point. It does not make a new performance optimization, change application/model settings, restart services, alter production data, merge another branch or rewrite history. The user's manual post-startup assessment exposed an unresolved speed problem before verification; see `SPEED_INCIDENT_2026-11-02.md`. It is not hidden by the historical faster reports.

## Executed checks

| Check | Observed result |
| --- | --- |
| `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v` | 222 run in 48.047 seconds; 221 passed, one skipped, no failures/errors. |
| Skip | Existing `test_history_refuses_symlinks`: this Windows installation cannot create the required symlink. |
| Rendering checks | The Python suite executed the production session renderer and profile renderer wrappers through Node. They cover 29 and eight controlled DOM/API scenarios respectively; these are not extra Python-test counts or live browser tests. |
| Python source validation | Reviewed new/modified Python files compiled from source in memory; no null bytes were found in the reviewed text files. No files were regenerated for this check. |
| Sensitive-file review | Reviewed application/test/docs candidates; no private-key or common GitHub/Hugging Face/OpenAI/AWS credential patterns found. Private storage, raw recordings, environments, downloaded models, local settings and ignored diagnostic outputs excluded from staging. Pattern scanning is supplemental review, not proof that every possible secret format can be detected. |
| `git diff --check` | Passed before staging. |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements found in the existing installed environment. |
| Running site | `/site-health` returned ready; served `accounts.js` SHA-256 matched the current working source. No server restart/launch was performed by the investigator. |

The suite includes unit/mocked speech boundaries, controlled subprocess lifecycle/failure tests, real temporary HTTP/SQLite authorization/session tests, and controlled JS rendering. It does not establish actual-model pronunciation accuracy or current real-user latency. Existing resource/deprecation warnings remain. Raw verification output stays in ignored `runs/publication-regressions-2026-11-02.log`.

No new investigator-driven real-model smoke or automated browser acceptance test was run during publication. The user manually ran the two actual-model assessments recorded in the speed incident; both completed but missed the target. Previous real-model/parity and browser evidence remains in the dated integration/polish reports. Incomplete broader human-recording cases, optional Kokoro execution and voice-preserving conversion remain unverified.

## Environment and reproducibility

Windows, application Python 3.13.1; inspected MFA 3.3.7 in a separate Conda environment. Installed NumPy 2.2.6, SciPy 1.15.3, Gradio 6.28.0, Torch 2.14.0+cpu and Transformers 5.17.0. Installed FastAPI 0.141.1/Uvicorn 0.53.0 differ from the existing declarations 0.143.0/0.54.0. Packages were not installed or upgraded to conceal this mismatch; a clean declared-environment test remains a teammate setup check.

Local resource/process reuse flags remain enabled and diagnostic/profiling flags remain disabled. The exact local paths and cached model weights are deliberately not published. A teammate must configure their own installation and measure it; cloning source alone does not reproduce Sarrvesh's prepared model state or historical latency.

## Commit boundaries

1. MFA resource caching, owned reusable interpreter/graph cache and their timing/lifecycle/failure tests. This remains separate from the earlier playback/UI fix.
2. Accumulated integrated application changes: original recording playback and immediate Practice results, revision/retry reliability, profile/guide/preferences, isolated optional generation adapter, offline research modules and focused tests. Existing edits overlap in shared UI files, so they are published as the reviewed integrated state rather than pretending to reconstruct independent historical UI commits. Teammate origins and ownership are recorded in the October 28/November 1 reports.
3. Current/historical engineering reports, interface addendum, README and teammate quick start. Reports preserve their original dates and claims; the new speed incident qualifies current readiness.

Unrelated older presentation exports under `output/presentation/` are left untracked and untouched. No account database, recordings, downloaded models or ignored local files belong in these commits. No push to `main`, teammate-branch merge or force-push is authorized or performed by this report. Final commit IDs and remote synchronization are verified after creating the scoped commits.

## Handoff

Read `TEAM_START_HERE_2026-11-02.md` for safe acquisition, setup, local configuration, teammate explanations, demonstration steps, outputs and limitations. Read the November 2 speed incident before quoting timings. Functional regression tests passed; reliable sub-ten-second operation is unresolved. Public deployment, validated grading, broader human acceptance and optional neural-generation model verification remain outside this publication.
