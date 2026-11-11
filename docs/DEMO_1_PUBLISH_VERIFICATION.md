# demo-1 publication verification

Date: November 10, 2026. Starting branch: `feature/speed-free-speech`, commit `529e28e79fd996b228f8d8309a0642aee5caea6b`. New branch: `demo-1`. Application snapshot tested from a clean clone: **52281f06c54372cf59fe245b9cbda3993936df31**. This subsequent verification memo changes documentation only.

## Included and preserved

The branch includes the current laptop app's complete source, previously untracked account/lesson-plan/recording/coaching modules, assets, focused tests, reports, optional AI adapter, setup guide and observed direct-package versions. `DEMO_1_SOURCE_MANIFEST.json` covers 238 snapshot files using LF-normalized UTF-8 or unchanged binary SHA-256. The manifest and this later memo are excluded from their own hash list.

The source of `pipeline.py`, `speech_content.py`, `analysis_service.py`, `confirmed_analysis.py`, `assessment.py`, `phoneme_scoring/`, `accounts/sessions.py`, `accounts/practice_jobs.py` and `voice_generation/` has no changes relative to the starting commit. Existing optimized MFA code/guards/locking and optional generation remain intact. Publication adds setup tooling/documentation, not a new analysis algorithm or concurrency setting. One pre-existing trailing space in the lesson-plan JavaScript was removed without a behavior change, and its manifest hash was updated.

No staging or publishing of private databases, human recordings, model weights, `.venv`, `.env` variants, screenshots/source backups under `output/`, machine-specific `settings.local.json` or caches. No matching credential patterns or files larger than 5 MB were found in the 238-file candidate audit. Pattern checks are not a universal secret-detection guarantee. Runtime secrets were not exported. Existing private data and local MFA settings were not changed.

## Executed checks

| Check | Actual result |
| --- | --- |
| Fresh local clone of `demo-1`, no model/environment copies | Created successfully. |
| All 238 manifest files verified in clone | No missing files or hash mismatches. |
| New module import locations | All resolved inside the clean clone, not the original workspace. |
| Clean-clone `python -B -m unittest discover -s tests -v` | **269 entries, 268 passed, 1 skipped, 88.742s.** |
| Existing skip | `test_history_refuses_symlinks`: this Windows installation cannot create symlinks. |
| `node --check web_assets/accounts.js` and `node --check web_assets/result_coach.js` in clone | Passed. |
| `git diff --check` in clone and full branch diff after the whitespace correction | Passed. |
| Installed app `python -m pip check` | No broken requirements found. |
| New `tests.test_demo_mfa_setup` | 4 passed: valid portable flags, invalid runtime rejection, no overwrite, UTF-8 without BOM. Included in full count above. |
| Setup helper with actual installed MFA metadata | Runtime accepted; executable, dictionary-cache location and reuse flags match the laptop. No config written or model executed. |

The clean clone used the laptop's existing Python 3.13 app interpreter/dependencies. **This is a clean-source verification, not a fresh package installation.** Some tests use real temporary private SQLite/HTTP/auth and most speech/provider paths use controlled doubles or fixtures. JavaScript suites run through Python wrappers; do not add their scenarios to the Python entry count as independent tests. Existing dependency deprecation/event-loop warnings remain.

The local full log is `output/demo-1-clean-clone-tests.log`, intentionally not published because local output directories are excluded. This summary records the observed result. No new human recording, live coaching-provider call, real-model speech benchmark, Azure VM, public-domain deployment or Linux port was tested for publication.

## Partner's next steps

Start with **[DEMO_1_START_HERE.md](DEMO_1_START_HERE.md)**. Clone `demo-1`, install the observed app requirements, separately download the pinned speech models/MFA resources, and create machine-local settings without copying laptop paths. Create your own account and verify a real short recording, original playback, private History, transcript correction and measured cold/warm processing.

For the closest reproduction use Windows x64. The current persistent MFA path and default desktop synthesis are Windows-specific. This source still binds localhost and enforces localhost Host/same-origin checks. Initial authorized VM-local testing or a separately configured SSH tunnel can preserve that behavior; public Azure hosting needs reviewed deployment settings and cloud privacy wording. Do not disable authorization/CSRF/runtime guards to force access or speed.

On a VM, the existing `ACCENT_COACH_DATA_DIR` can point to a durable private directory outside the checkout. `ACCENT_COACH_OPEN_BROWSER=0` suppresses automatic browser opening. Keep private storage backed up and access-restricted; Git does not synchronize account/recording data. Optional AI/Kokoro remain disabled/unconfigured until separately approved and tested. No transferred ten-second performance guarantee is made.
