# Optional AI coaching verification, November 10, 2026

## Result and scope

Implemented locally on `feature/speed-free-speech`, HEAD `529e28e79fd996b228f8d8309a0642aee5caea6b`. Nothing was staged, committed, pushed, reset or merged. Existing playback, speed, reliability, personalization and UI work was retained. Task-start source backups and task-specific diffs are in `output/ai-coaching-baseline/` and `output/ai-coaching-own-*.diff`.

Coaching is optional and disabled: no approved runtime model/provider credentials were found or configured. No live AI request or paid API call was made. The production speech pipeline remains authoritative. The default page shows the saved result, original audio, existing next/retry actions and a disabled Explain button with a clear setup message; it does not download `result_coach.js`. A configured provider gets an explicit button, loading area, bounded explanation, approved tip/exercise, safe failure copy and explicit retry.

Current route/storage hardening was verified with isolated FastAPI/SQLite tests. The final route-wide authentication deadline and optional-migration failure safeguard were added after the last manual app restart; restart before enabling a provider to load these final Python edits. Live browser checks below verified the default-disabled UI, existing base results, privacy text and original playback. They do not establish a live configured coaching integration.

## Flow and preserved components

- Existing capture/playback: `web_assets/microphone.js`, the original-source player in `web_assets/accounts.js`, and authenticated original/role-specific audio routes in `accounts/web.py`.
- Existing speech and eligibility: `speech_content.py`, `pipeline.py`, `confirmed_analysis.py`, `assessment.py` and `phoneme_scoring/`. These files, MFA settings, model configuration, locking, caching and inference were not changed by this task.
- Existing private persistence and revisions: `accounts/store.py`, `accounts/sessions.py`, `accounts/practice_jobs.py`; this task does not alter their analysis/progression decisions. Previously uncommitted changes to Store remain separate.
- Existing completion/plans: `accounts/lesson_plan.py` and its persisted step records. Coaching reads these records without calling a plan-reconciliation writer. It cannot complete steps or save/modify base results.
- New optional path: typed `ai_coaching/contract.py` and evidence projection → authenticated `CoachingService` → owner/version-scoped SQLite cache → one configurable text-only provider call → closed-world validation → plain-text secondary UI. No audio, account/email names, URLs or unrelated History are included in model input.

Target present with different surrounding words is explained as insufficient qualified evidence, not automatically a missing word or an error. Existing full-content eligibility is not bypassed. Empty ASR text, unavailable transcription, unsupported dictionary/model coverage, detected clipping/silence and technical failure remain distinct. Repeated targets retain the actual saved word index when available. AI output never changes result category, score, eligibility, progress, saving or actions.

## Tests actually executed

| Command | Outcome | Evidence type |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` | 265 entries; 264 passed, 1 skipped; 124.732s | Existing regressions plus coaching, real temporary auth/SQLite/HTTP and controlled speech/provider doubles. Log: `output/ai-coaching-verified-final.log`. |
| `.\.venv\Scripts\python.exe -m unittest tests.test_ai_coaching -q` | 20 passed; 8.215s | Focused contract/provider/cache/ownership/deadline tests. Log: `output/ai-coaching-accepted-python.log`. |
| `node --test tests/session_playback.cjs` | 85 passed | Production JS with controlled DOM/HTTP/media doubles. Log: `output/ai-coaching-accepted-ui.log`. |
| `node --check web_assets/accounts.js` and `node --check web_assets/result_coach.js` | Passed | Syntax checks. |
| `git diff --check` and UTF-8/null-byte scan of new source | Passed | Working-tree/source checks. |

The JavaScript wrapper is already one entry in the Python suite; do not add the counts as independent unique totals. The existing skipped check is `test_history_refuses_symlinks`: this Windows installation cannot create symlinks. Existing Starlette/httpx deprecation and event-loop warnings remain; no package was installed or upgraded.

Covered: all six result categories; case/punctuation/whitespace; missing target versus different context; empty text; unsupported coverage/audio claims; injection strings and evidence delimiters; contradictory output/unknown IDs/extra fields; one HTTP generation without retries; refusal/oversized response/rate limit; absent credentials/disabled provider; provider and route deadlines; duplicate clicks/concurrent requests; edit/navigation abort and late responses; actual private owner/revoked-session checks; learner identity and revision invalidation; prompt/provider/plan cache changes; cache persistence and deletion; cache migration failure; no base-result/audio/progress mutation. `contracts/evaluations/coaching_v1.json` is a versioned 13-case grounding set plus two cross-runtime fingerprint fixtures. It is not a human pronunciation-accuracy dataset.

No new real-model speech inference, fresh human recording, live-provider completion or broad coaching-usefulness evaluation was executed in this task. Existing speech behavior has regression coverage and the real saved-result browser checks below; unchanged source is not evidence of a new under-ten-second benchmark.

## Actual browser checks

- Matching preset, transcript mismatch and inconclusive free-speech saved results restored through the actual signed-in app. The default Explain action was disabled, the setup message was visible, no optional coaching script was loaded and no new browser console errors were observed.
- Opened the saved free-speech result through View in History: original asset duration 3.18s, actual keyboard-started playback, same source/duration after refresh.
- Opened the saved mismatch preset through View in History: original duration 2.304s, actual playback, same source/duration after refresh. Selected and recognized words stayed distinct and recovery preserved the preset lesson.
- The actual Privacy page exposed the optional-coaching notice. No external provider was enabled or sent private text/audio.
- Separate, explicitly labeled sample-provider browser fixtures verified loading → explanation, friendly failure → explicit retry, and usable original-player controls. Sixteen combinations (four result fixtures × outer frame widths 360/390/768/1140px) showed no horizontal overflow. Effective content widths were 340/370/748/1120px because of Windows scrollbars. These are rendered iframe checks, not physical-phone acceptance.
- At CSS page zoom 2, keyboard playback remained active and focus stayed on Your recording while simulated coaching arrived; no horizontal overflow was measured. Native browser zoom and a real screen reader were not verified.

Screenshots: `output/ai-coaching-actual-disabled-ui.png` is the actual app. `output/ai-coaching-simulated-ui.png` uses a simulated provider and must not be presented as a live AI result. The temporary preview server was stopped; the user app was left running.

## Timing method and limits

Times below are milliseconds. Browser samples use an outer wall clock from navigation through separate visible-result, saved-status and playable-player waits. They include automation/IPC, navigation, fetch, asset caching and rendering overhead. Save acknowledgement means the restored result was already persisted, not the duration of a new database save. Player readiness is metadata/player availability, not proof of uninterrupted decoding for an entire clip. These tests did not submit analysis or re-run ASR/MFA.

Actual signed-in restore: same three owned saved cases, three runs each, before and after. Earlier/later sampling, app restarts, asset-cache state and machine load were not controlled tightly enough to attribute all differences to this change. Every run, including slow samples, is retained below. The first post-change series overlapped regression testing; it is not a clean causal comparison. A later idle series and a final simplified-disabled-path series are reported separately. No result is silently discarded.

| Series | n | Median result visible | Median saved acknowledgement | Median player ready |
| --- | ---: | ---: | ---: | ---: |
| Before | 9 | 334.0 | 347.0 | 472.0 |
| Initial post-change, test workload | 9 | 988.0 | 1092.0 | 1137.0 |
| Post-change, tests idle | 9 | 708.0 | 752.0 | 854.0 |
| Final simplified disabled path | 9 | 506.0 | 589.0 | 721.0 |

Final actual median visible time was 506ms versus 334ms earlier (172ms higher). This is an observed restore difference, not a measured change in speech-model latency. The initial slowdown prompted the simpler disabled path, removing its optional module download and provider work. Confounding load/cache differences prevent a causal speed claim.

For a more controlled UI-only check, the pre-task and final account-renderer sources alternated six times each against identical fixture responses, current CSS, a static WAV and the same browser/server. No provider was active. All first and later loads are retained; cache state was not forcibly cold.

| UI fixture source | n | Median result visible | Median saved acknowledgement | Median player ready |
| --- | ---: | ---: | ---: | ---: |
| baseline | 6 | 276.0 | 323.5 | 347.5 |
| changed | 6 | 312.5 | 345.0 | 367.5 |

The matched fixture median increase was 36.5ms for visible result, 21.5ms for saved acknowledgement and 20ms for player readiness. The small sample and wall-clock/IPC variability do not establish statistical significance. The implementation therefore does not claim zero latency impact. It adds no generation to the base-result path. New-recording inference and new-save latency were not measured.

### Individual signed-in restore runs

| Series | Case | Run | Visible | Saved acknowledgement | Player ready |
| --- | --- | ---: | ---: | ---: | ---: |
| Before | expected | 1 | 820 | 841 | 866 |
| Before | expected | 2 | 326 | 347 | 381 |
| Before | expected | 3 | 334 | 343 | 472 |
| Before | mismatch | 1 | 277 | 293 | 310 |
| Before | mismatch | 2 | 470 | 497 | 618 |
| Before | mismatch | 3 | 427 | 435 | 550 |
| Before | inconclusive | 1 | 486 | 503 | 520 |
| Before | inconclusive | 2 | 232 | 242 | 358 |
| Before | inconclusive | 3 | 330 | 341 | 460 |
| Initial post-change, test workload | expected | 1 | 988 | 1092 | 1137 |
| Initial post-change, test workload | expected | 2 | 680 | 828 | 858 |
| Initial post-change, test workload | expected | 3 | 646 | 745 | 790 |
| Initial post-change, test workload | mismatch | 1 | 642 | 723 | 755 |
| Initial post-change, test workload | mismatch | 2 | 734 | 797 | 827 |
| Initial post-change, test workload | mismatch | 3 | 1358 | 1426 | 1940 |
| Initial post-change, test workload | inconclusive | 1 | 1121 | 1342 | 1385 |
| Initial post-change, test workload | inconclusive | 2 | 1108 | 1151 | 1310 |
| Initial post-change, test workload | inconclusive | 3 | 1307 | 1360 | 1414 |
| Post-change, tests idle | expected | 1 | 833 | 1038 | 1291 |
| Post-change, tests idle | expected | 2 | 669 | 883 | 936 |
| Post-change, tests idle | expected | 3 | 447 | 662 | 829 |
| Post-change, tests idle | mismatch | 1 | 465 | 683 | 871 |
| Post-change, tests idle | mismatch | 2 | 287 | 347 | 569 |
| Post-change, tests idle | mismatch | 3 | 990 | 1094 | 1128 |
| Post-change, tests idle | inconclusive | 1 | 794 | 829 | 854 |
| Post-change, tests idle | inconclusive | 2 | 708 | 742 | 787 |
| Post-change, tests idle | inconclusive | 3 | 710 | 752 | 769 |
| Final simplified disabled path | expected | 1 | 643 | 740 | 894 |
| Final simplified disabled path | expected | 2 | 587 | 681 | 754 |
| Final simplified disabled path | expected | 3 | 506 | 589 | 733 |
| Final simplified disabled path | mismatch | 1 | 495 | 589 | 625 |
| Final simplified disabled path | mismatch | 2 | 613 | 683 | 721 |
| Final simplified disabled path | mismatch | 3 | 451 | 560 | 620 |
| Final simplified disabled path | inconclusive | 1 | 459 | 524 | 554 |
| Final simplified disabled path | inconclusive | 2 | 481 | 552 | 587 |
| Final simplified disabled path | inconclusive | 3 | 629 | 740 | 795 |

### Individual alternating UI fixture runs

| Run | Source | Visible | Saved acknowledgement | Player ready |
| ---: | --- | ---: | ---: | ---: |
| 1 | baseline | 906 | 970 | 1025 |
| 1 | changed | 293 | 318 | 342 |
| 2 | changed | 282 | 314 | 337 |
| 2 | baseline | 322 | 349 | 371 |
| 3 | baseline | 278 | 316 | 343 |
| 3 | changed | 332 | 432 | 474 |
| 4 | changed | 403 | 437 | 462 |
| 4 | baseline | 274 | 331 | 352 |
| 5 | baseline | 249 | 300 | 329 |
| 5 | changed | 248 | 288 | 310 |
| 6 | changed | 343 | 372 | 393 |
| 6 | baseline | 231 | 270 | 298 |

### Optional service/cache measurements

Command: `.\.venv\Scripts\python.exe tools/benchmark_optional_coaching.py`. Real temporary private SQLite/service logic with a deliberately 20ms fake provider; **not live AI latency**. Five uncached generations and five same-owned-evidence cache reads, all completed. Exactly five provider calls. Service/cache-table preparation was 12.95ms (n=1), excluding Store/account initialization and application startup. No audio/model processing was performed.

| Case | Fake-provider request elapsed | Validated owned-cache elapsed |
| ---: | ---: | ---: |
| 1 | 83.89 | 19.85 |
| 2 | 57.72 | 16.24 |
| 3 | 48.83 | 13.75 |
| 4 | 54.95 | 13.89 |
| 5 | 61.80 | 14.23 |

Median fake-provider service elapsed: 57.72ms; median validated cache lookup: 14.23ms. These include real evidence/auth/cache validation and the simulated provider delay. They cannot predict the configured model or network. Live coaching latency has n=0 and remains unmeasured; production has an initial maximum five-second optional deadline.

## Files and setup

New: `ai_coaching/{contract,evidence,provider,repository,service}.py`, `ai_coaching/prompts/explain_v1.txt`, package initializer, `web_assets/result_coach.js`, `tests/test_ai_coaching.py`, evaluation fixtures, `tools/benchmark_optional_coaching.py`, and the two coaching documents. Modified for this task: `accounts/web.py`, `site_server.py`, `site_pages.py` (privacy only), `web_assets/accounts.js`, `web_assets/ui-polish.css`, `tests/session_playback.cjs` (coaching and intentional result-layout expectations). Existing other dirty/untracked files are not attributed to this task and were not staged.

Runtime setup and privacy are in `docs/OPTIONAL_AI_COACHING.md`. The adapter needs an explicit compatible endpoint/model, a server-side key for an external endpoint, explicit server external enablement and a user disclosure choice. Credentials are never sent to the browser or logged. The bounded model response is selected from reviewed explanations/approved IDs; the tradeoff is less free-form personalization. Only English is supported initially. Provider retention/training practices are unverified and not promised.

## Remaining work and recommendation

1. Select and approve a compatible runtime provider/model; review its actual data handling, configure credentials server-side, then restart. Keep disabled until this is done. No provider identifier or key has been invented.
2. Run a bounded live evaluation of the versioned fixtures and a small human usefulness review. Check actual provider schema compatibility, refusal/timeout behavior, language clarity and optional latency. Do not infer pronunciation-detection accuracy from this exercise.
3. Verify a real configured coaching response/cache after refresh and History navigation, with two authorized browser accounts. Real private ownership/cache enforcement is automated; live configured-provider browser persistence is not yet established.
4. Complete physical-phone, native increased-browser-zoom, screen-reader and fresh-human pronunciation acceptance testing separately. Rebenchmark new-recording ASR/analysis if a new speed guarantee is required.

Retain this optional implementation. The default application and its authoritative analysis remain usable without AI; unsafe or unavailable generation falls back rather than changing a judgment. No pronunciation-detection accuracy improvement, live-provider success or universal under-ten-second performance is claimed.
