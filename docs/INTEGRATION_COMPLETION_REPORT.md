# Private practice integration report

October 13, 2026. Branch: `feature/speed-free-speech`.

## Completed and checked

- Published the five verified Day 2 commits through `2d42433` to origin/feature/speed-free-speech.
- Applied Lucas's uploaded account patch from `76cef88` and imported Parthiban's generation component from `09f6de1`. Neither teammate branch was modified or merged. The user approved both integration commits and their push; the first integration commit is `74978dc`.
- The main private website now supports preset lessons, custom text and free speech. For new modes: upload/record -> independent transcription -> review/edit -> explicit confirmation -> queued analysis. No preset ID or reference waveform is required for custom/free modes.
- Added flat session snapshots, immutable learner asset IDs, job IDs, revisions and atomic result acceptance in Lucas's existing SQLite database. No separate persistent session store was introduced. Every new read, edit, job and audio route revalidates the login-session token and ownership. Client user IDs are ignored as authorization.
- Replacing audio or changing confirmed text invalidates dependent outputs. Late jobs cannot publish after edits, retries, deletion or logout. Duplicate active submissions reuse the existing job receipt. The bounded shared queue reports BUSY explicitly; legacy and confirmed speech jobs use one reusable worker.
- Private generated WAVs are stored under separate server-assigned synthetic roles and authorized playback routes. Current registered generated WAVs are rejected if re-uploaded as learner recordings through either practice path. Role/identity separation does not prove that every arbitrary uploaded waveform is human speech, especially transformed or previously unregistered files.
- Added generation adapter mapping to the agreed flat session fields and shared 12-word/200-character scope. Parthiban's standalone development fixture adapter now accepts the approved flat fixture; its internal nested representation is not the main site's public API.
- Synthetic playback works through Parthiban's Windows System.Speech backend (Microsoft David Desktop here). The app labels it synthetic and does not claim voice preservation or validated accent quality. Kokoro's isolated environment and weights are absent here; they were not installed into the shared speech environment.
- Added recognition-model ID/revision compatibility checks to the existing audio-fingerprint checks. Old/incompatible saved recognition cannot authorize decisive feedback. Worker elapsed time now includes final assessment/result formatting and cleanup; account-job timing covers the worker call, including worker startup when applicable.
- Profiles and suggestions work with both preset results and custom/free sound results. Inconclusive findings do not become mistakes or improvement scores.
- Installed the declared Argon2 account dependency, without upgrading speech packages. Dependency checks pass. Added its installed binding version to the account requirements.
- Updated practice/help controls, private history, deletion, responsive textarea styling and error messages. Transcript editing preserves the original recognized text and hides dependent results until reconfirmation. Polling preserves the editor and generated playback when their content is unchanged.

## Actual verification

| Check | Command / evidence | Result |
| --- | --- | --- |
| Full suite after integration | `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v` | 155 tests: 154 passed, one existing Windows symlink skip; zero failures. `runs/integration-verified.log` |
| Private session integration | tests/test_practice_sessions.py (included above) | Real HTTP/login/SQLite/ownership/revision transactions; controlled speech/generation doubles. Checks two users, limits, duplicate jobs, BUSY, stale edits/deletion/logout, restart recovery, generated-wave rejection and suggestions. |
| Real private flow | `.\.venv\Scripts\python.exe -B tools/check_private_free_speech.py` | 17 checks passed using actual Whisper, MFA, phoneme inference, Windows synthesis, private playback and SQLite. `runs/private-free-speech-smoke.json` |
| Direct launcher environment | Real align_audio call using active local settings | Available alignment for existing local demo recording, words i/think/so; 30.405 seconds total. `runs/direct-launch-real-check.json` |
| Launcher A/B study | `.\.venv\Scripts\python.exe -B tools/compare_mfa_launch.py` | Six successful alignments, all three paired word/phone/boundary/audio outputs equal. |
| JavaScript | `node --check web_assets/accounts.js` | Passed |
| Dependencies | `.\.venv\Scripts\python.exe -m pip check` | No broken requirements |
| Preview | GET http://127.0.0.1:7861/site-health | ready, public_launch=false |

The real-flow test uses the existing local demo recording with confirmed text I think so. Repeated-word and contraction cases change that transcript to I think I think so and I don't think so; they intentionally disagree with the actual recording. Both completed conservatively with inconclusive feedback. They do not establish reliable assessment of newly spoken repetitions/contractions or pronunciation accuracy. The real flow uses temporary test accounts/database and cleans them up; the running preview starts with its own local account database.

The initial integrated suite exposed 11 generation fixture/schema errors, which were corrected. The first real generation attempt exposed an asset-ID/file-path adapter mismatch; it was fixed and the complete real flow was rerun successfully. Existing Starlette/httpx and event-loop warnings remain. Later small UI preservation/help changes were syntax-checked and covered by the final suite; microphone interaction still needs manual browser checking.

## Measured speed change

Same synthetic benchmark clip (1.73 seconds), text, installed dictionary/acoustic model, MFA settings, file lock and fresh output directories. Three alternating Conda/direct pairs; installed files warm, no downloads/cache clearing. No other project test or analysis job ran during the launcher study. OS background load is uncontrolled, and Conda always precedes direct in each pair.

| Pair | Conda total (s) | Direct total (s) | Alignment outputs |
| --- | ---: | ---: | --- |
| 1 | 37.695 | 32.950 | Equal |
| 2 | 33.151 | 30.123 | Equal |
| 3 | 32.549 | 30.088 | Equal |
| Median | 33.151 | 30.123 | All three equal |

Observed median reduction: 3.028 seconds, approximately 9.1% for this alignment operation. This is not a whole-app improvement percentage or a guarantee across recordings. MFA remains the main slow stage; model loading and different audio/text can increase total latency.

Direct launching is enabled **only on this laptop** in ignored `phoneme_scoring/settings.local.json`, with child-only PATH/CONDA_PREFIX overrides for the installed MFA environment. The prior configuration is backed up in `runs/mfa-conda-settings-backup.json`. Other machines retain their own setup; no personal environment path is proposed for Git. Locks, inference parameters and timeouts remain in place. The launcher study script explicitly constructs its Conda baseline so it stays reproducible after local activation.

## How to check the app

1. Open http://127.0.0.1:7861/. Create your own local account or sign in.
2. Try Preset lesson with an existing core recording to check the preserved route.
3. Choose My own sentence or Free speech. Record/upload a WAV of five seconds or less. For text, stay within 12 words and 200 characters.
4. Save/transcribe, inspect the recognized words, edit if needed, then press Confirm transcript. Analysis and generation require confirmation.
5. Press Analyze confirmed words. Supported/practice/inconclusive are experimental sound outcomes, not grades. Recognition disagreement withholds judgments.
6. Press Hear a synthetic example. Playback is a generated desktop voice, not your converted voice. Verify the original recording remains separate.
7. Check My history and My profile. Sign in as another account and confirm the first account's history/playback is unavailable. Automated tests already cover the direct API checks.

Preview runs locally on 127.0.0.1:7861. A fresh launch command is `.\.venv\Scripts\python.exe app_2.py`; do not launch another copy on the occupied port. Stop the current preview before restarting to load future code changes. The preview process ID is in ignored `runs/private-preview.pid`.

## Remaining work

- Record actual consented custom, repeated-word and contraction utterances. Review unknown-word handling, microphone permissions and the full browser recording flow manually. Current automated tests do not supply those new spoken clips.
- Validate sound judgments with independent human labels and held-out speakers before adding a trustworthy grade or improvement score. The app currently tests TH, IH and AE contrasts, not every accent feature.
- Install/test Parthiban's isolated Kokoro runtime if the team chooses its voice quality over the functioning Windows backend. Independently review generated words/accent/naturalness. Voice-preserving conversion remains unimplemented stretch work.
- Measure a wider/randomized launcher sample and whole-app latency on equivalent work. Larger optimization or hardware changes are not yet validated or provisioned.
- Choose domain/hosting, HTTPS and production retention/security requirements before public deployment. Current preview is localhost only.
- Reconcile with Lucas and Parthiban before promotion to the integration branch. Their branches were preserved and no merge to main was performed.

## Approved commit scopes

1. **Integrate authenticated accounts, generation and confirmed practice:** Lucas-derived accounts/site/UI/requirements files; imported voice_generation component and its tests; accounts session/job adapters; shared worker/confirmed-analysis safeguards; all corresponding tests and private-flow tool.
2. **Enable measured local MFA launch support and document integration:** optional child-environment support in align_audio and timing test; launcher-comparison tool; smoke-tool environment compatibility; this report and shared-interface/readme addenda. The ignored local settings and raw runtime evidence are excluded.

The user approved staging, creating and pushing these two scoped commits on October 13, 2026. The first is `74978dc`; the second contains this report and can be identified in Git history by its MFA launch support/documentation title. The verification results above were recorded before committing. Remote publication is verified separately after the push. Ignored local settings, recordings, runtime evidence and private account data are excluded from both commits.
