# Team feature integration, October 28, 2026

## Result and scope

Integrated compatible American practice guidance, a saved optional Mandarin learner profile, and an opt-in isolated Kokoro connection into the current application. Sarrvesh explicitly selected all three additions. Existing teammate accounts, private History and basic desktop synthesis were already present; they were preserved rather than reapplied.

Branch and HEAD remain `feature/speed-free-speech` / `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`. No staging, commit, push, reset, stash, checkout or ancestry merge was performed. No dependencies, model weights, dictionary entries, settings or inference thresholds were changed. This is a selective port from inspected teammate commits, not a wholesale merge of their older application snapshots.

**Speed was preserved in the executed isolated sample:** reused-worker median transcription-plus-analysis time was 5.609 seconds before and 5.633 seconds after. The difference is 0.024 seconds (about 0.43%); no material median regression was observed in this small sample. All six paired alignments, sound results, limitations, recording identities, revisions and confirmed transcripts matched. This is not a browser-latency guarantee or a strict ten-second maximum.

## What is available in the app

### American practice

Lucas's `origin/american` at `e4117e2` supplied the draft target data now in `practice_targets.json`. The Practice page displays three guides: I think so; The bed is bad; The ship is here. Each has sentence IPA, word IPA, focus sounds and accepted-variation explanations. They are explicitly educational targets, not detected pronunciation findings.

`Practice these words` selects the existing custom-text workflow, fills the intended sentence and clears abandoned UI/recording state. The learner must provide a new recording, review transcription and explicitly confirm words before analysis. Guide viewing alone never runs a model or relabels a saved result. An unavailable guide API leaves the original recorder usable.

No second analysis pass, all-phoneme grading, 15-second scope, heuristic Correct/Incorrect UI, or replacement scorer was imported. The current five-second/10-MB recording limits, 12-word/200-character text limits and eligible TH/IH/AE assessment scope remain intact. Existing preset lessons are preserved.

### Mandarin learner guidance and offline research

My profile now offers General practice and Mandarin-speaking learner. The selection is explicit and private; it never infers ethnicity, language or mistakes from a voice. General American remains the target accent in both cases. The current preference changes guidance only, not assessment inputs, thresholds, judgments or past result interpretation. It does not claim trained Mandarin-specific ratings.

The preference uses an additive `practice_preferences` table in the existing SQLite database. Existing users default to general. Older clients omitting the optional field preserve the saved preference. Updates use the authenticated account and a transaction; invalid selections cannot partially update the display name/goals. Tests verified two-account separation, restart persistence and opening an older database without changing its users. The production account database was not directly edited by scripts; normal startup creates the additional table.

Lucas's `origin/chinese` at `231a8b3` supplied the profile and offline modules. Files uploaded at repository root were placed at the package paths their imports require:

- `accent_profiles.py`, `accent_profiles/chinese.json`
- `phoneme_scoring/calibration.py`, `calibrate_scores.py`, `speechocean_data.py`, `evaluate_speechocean.py`

The annotation adapter now accepts current alignment `word_id`/`word` fields and retains repeated-word occurrence positions. Dataset recording paths cannot escape the configured dataset root; piped commands remain rejected. The offline evaluator and fitter CLI help commands work. Tests cover absent/incompatible calibration, abstention, speaker-separated development data, rejecting official test data/duplicates, annotation mismatches, repeated occurrences and path escape.

**These research tools are not imported or executed by live assessment.** No SpeechOcean corpus, fitted calibration model or held-out-speaker accuracy evaluation is available here. Enabling calibrated live ratings requires a separate design/validation task; merely importing the research modules is not evidence of a trained grader. Example offline commands, after obtaining the dataset legitimately, are:

```powershell
.\.venv\Scripts\python.exe -m phoneme_scoring.evaluate_speechocean --root <local-dataset-folder> --split train --limit 20 --output runs/mandarin-smoke-new
.\.venv\Scripts\python.exe -m phoneme_scoring.calibrate_scores runs/mandarin-smoke-new/phone_rows.jsonl
```

The small evaluation limit is only a setup smoke, not adequate calibration evidence. Use separate training/development/test speakers and report excluded coverage before relying on any fitted ratings. No dataset command was run in this integration.

### Optional Kokoro

Parthiban's Kokoro backend and generation component from `origin/feature/voice-conversion` at `09f6de1` were already imported. The new `voice_generation/runtime.py` and `external_worker.py` connect them to the existing private generation jobs using a separately configured Python interpreter. The subprocess starts lazily, reuses its model, and communicates over private JSON stdin/stdout. It does not import or change Torch/spaCy/Transformers inside the assessment interpreter.

The default backend remains the exact existing Windows generation callable. Kokoro is **off by default and not activated on this laptop**. Its dedicated environment, model/voice assets and spaCy package are missing. The adapter was tested with controlled real subprocesses/backend doubles; real Kokoro synthesis, quality, memory and latency were not tested here. Real desktop generation and authorized playback did pass.

The optional boundary enforces 12 words/200 characters, safe synthetic IDs, readable nonempty WAV output, a 120-second generation deadline, owned process-tree cleanup, removal of new partial outputs and explicit failure/retry messages. Existing ownership/revision/job checks still control publication. A generation failure cannot replace completed analysis. Generated assets remain separate from learner recordings. No voice-preserving conversion is implemented.

See `OPTIONAL_KOKORO_SETUP.md` for explicit activation/fallback. Keep the desktop backend for the speed demonstration until Kokoro is separately measured. Generation and assessment still share the existing bounded serial scheduler; neural generation could queue analysis and add memory pressure. Process separation alone is not a guarantee against hardware contention.

## Performance verification

Used the existing `runs/speed_20261027.py --mode persistent --flow confirmed` harness before edits and after integration. Both serial series used the same three previously supplied, consented saved waveforms, confirmed transcripts, settings, cache flags, pinned models and six-request order. Each series created a fresh isolated assessment worker and reused it for requests 2–6. No application analysis job competed during the series. Existing timers/observer instrumentation were used; no instrumentation was added to application code.

These are read-only reassessments of existing recordings, not six newly recorded human cases. Each request ran transcription and real alignment/scoring again; no assessment-result cache was used. The source/production-preservation checks passed for both series. Every warm request reported interpreter reuse, compiled dictionary hit, two graph-resource hits and no graph fallback. First requests populated the in-memory graph cache.

| Group | First request | Warm median (5) | Warm range | Completion |
| --- | ---: | ---: | ---: | --- |
| Before | 86.132 s | 5.609 s | 4.855–5.903 s | 6/6 |
| After | 32.979 s | 5.633 s | 5.400–5.934 s | 6/6 |

First-use figures include model/import/resource preparation and differ substantially; the first transcription was 60.413 seconds before versus 14.977 seconds after. Sequential OS/file-cache/background conditions were not controlled or randomized. **Do not call that startup difference an improvement caused by this integration.** Both first-use results exceed ten seconds.

The individual request table is appended below. Times are seconds. Total includes transcription and analysis; ASR wall time includes any initial assessment-worker startup. MFA execution includes process initialization when marked fresh. Remaining outer overhead is not assigned to invented stages.

| Group | Request | Clip | Worker | Total | ASR wall | MFA lock | MFA execution | Phoneme |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Before | 1 | think | fresh | 86.132 | 60.413 | 0.0018 | 16.819 | 3.734 |
| Before | 2 | ship | reused | 5.609 | 1.190 | 0.0003 | 2.691 | 0.864 |
| Before | 3 | bad_bed | reused | 5.695 | 1.183 | 0.0004 | 2.651 | 1.055 |
| Before | 4 | bad_bed | reused | 5.903 | 0.940 | 0.0005 | 3.107 | 0.850 |
| Before | 5 | ship | reused | 4.855 | 0.966 | 0.0004 | 2.321 | 0.728 |
| Before | 6 | think | reused | 4.921 | 1.105 | 0.0003 | 2.203 | 0.806 |
| After | 1 | think | fresh | 32.979 | 14.977 | 0.0007 | 12.975 | 2.203 |
| After | 2 | ship | reused | 5.633 | 1.188 | 0.0005 | 2.695 | 0.803 |
| After | 3 | bad_bed | reused | 5.400 | 1.083 | 0.0006 | 2.402 | 0.927 |
| After | 4 | bad_bed | reused | 5.776 | 1.193 | 0.0005 | 2.711 | 0.918 |
| After | 5 | ship | reused | 5.463 | 1.032 | 0.0006 | 2.624 | 0.842 |
| After | 6 | think | reused | 5.934 | 1.049 | 0.0005 | 3.027 | 0.912 |

All six before/after pairs matched complete alignment words/segments/boundaries/audio identity and the published sound results/limitations. No result was dropped, retried or replaced. The highest warm after time was 5.934 seconds. This small sample does not establish population tail latency, multiple-user throughput, new-human accuracy or browser performance. Kokoro was disabled throughout.

## Verification executed

| Check | Observed result |
| --- | --- |
| Full suite: `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v` | 214 tests run in 59.510 seconds: 213 passed, one existing Windows symlink-creation skip, zero failures. Covers unit/model doubles, controlled subprocess recovery, real temporary HTTP/SQLite and the JS wrapper. |
| Final UI rendering: `node --check web_assets/accounts.js`; `node --test tests/session_playback.cjs` | Syntax passed; all 28 production-renderer scenarios passed, including guide selection/reset, failure fallback and profile payload. This is controlled DOM/HTTP testing, not physical browser/audio acceptance. |
| Final account HTTP regression: unittest discovery for `test_accounts_integration.py` | All seven tests passed after final UI label changes. |
| Real integrated smoke: `.\.venv\Scripts\python.exe -B runs/teammate-integration-real-smoke.py` | 20 checks passed: temporary authenticated accounts/SQLite, saved Mandarin preference, guide API, unchanged target/no grade, actual Whisper/MFA/phoneme inference, Windows synthesis, authorized playback and generated reupload rejection. |
| Six paired benchmark cases | 12 completed requests; all six identity/revision/text/outcome/limitation and complete alignment comparisons matched. |
| Live browser after source repair | Signed-in Practice displayed all three guides. The bed guide selected custom text, filled the sentence, retained the recording-required/confirmation flow and cleared obsolete preset labels. Profile offered Mandarin; the selection was inspected without saving, and reload restored the original general preference. No captured console warnings/errors. No microphone/upload/analysis was simulated as browser acceptance. |
| Source validation and hygiene | All 89 project Python source files compiled; `app_2` imported without launching a server; `git diff --check` passed; index remains empty. |

Initial new-test issues were corrected: one test fixture left a temporary SQLite connection open on Windows, and one renderer failure-injection flag was shadowed by request options. Neither was hidden as a pass; corrected tests were rerun successfully. Existing dependency warnings remain; no packages were upgraded to suppress them.

The real smoke uses the existing I think so demo. Repeated/contraction confirmed text deliberately disagrees with that waveform and correctly remains inconclusive. Those are guard checks, not successful human pronunciation-accuracy acceptance. No real Kokoro or fitted Mandarin calibration is claimed.

## Startup error repaired

The user reported `SyntaxError: source code string cannot contain null bytes`. Inspection found `site_pages.py` contained 15,340 null bytes and no source text; the other active Python sources had no null bytes. The corruption's cause was not established.

Saved the damaged bytes as ignored diagnostic evidence, restored `HEAD:site_pages.py` with the original CRLF representation, and verified that it exactly matched the pre-integration source hash recorded before work. Then applied only the intended privacy-copy addition describing the optional saved learner-guidance preference. The module now compiles/imports and the actual browser app opens. No speed module, settings, user recordings or account rows were reset to repair it.

## Preservation, files and rollback

Existing analysis code, MFA execution/cache code, model settings, recording/text limits, confirmed-text/audio identity checks, input revisions, stale publication rejection, uncertain/unsupported handling, original playback and current Practice/History results remain preserved. The following were verified byte-identical to the start of this task: `analysis_service.py`, `pipeline.py`, `confirmed_analysis.py`, `speech_content.py`, `accounts/sessions.py`, `phoneme_scoring/align_audio.py`, `gop_score.py`, `persistent_mfa.py`, `mfa_worker.py`, `fst_resource_cache.py`, `mfa_dictionary_cache.py` and ignored local settings. Existing CSS was not replaced.

Only seven preexisting files changed in this task: `accounts/store.py`, `accounts/web.py`, `accounts/practice_jobs.py`, `web_assets/accounts.js`, `tests/session_playback.cjs`, `site_pages.py` (privacy copy after repair) and `docs/TEAM_INTERFACE.md`. New files comprise the seven selected teammate data/research files, `practice_guides.py`, the two generation adapter files, three test modules and the two integration/setup reports. The complete dirty inventory includes substantial earlier work; it must not be treated as all belonging to this change.

Evidence and pre-edit snapshots: `runs/teammate-integration-20261028T225207Z/`. Benchmark files are `runs/speed-20261028T225210Z-persistent-confirmed/measurements.json` and `runs/speed-20261028T225941Z-persistent-confirmed/measurements.json`. Individual artifacts include `preservation.json`, `speed-comparison.json`, `alignment-parity.json`, `real-integrated-smoke.json`, test logs and browser screenshots. No raw voice or production account database was copied into the report directory. Source snapshots exclude credentials.

Prefer reverting only this task's reviewed hunks if rollback is needed; do not reset the whole dirty checkout. The new preferences table is additive and older code ignores it. Keep it rather than deleting account data. To disable neural examples, restore the default Windows backend as documented; no MFA change is needed. Raw older teammate app/scoring files were never installed over the current code.

## Next actions and commit scopes

1. Current app is usable with desktop generation. Try the new guides and optional profile normally; broad fresh-human acceptance cases remain unfinished.
2. Keep Kokoro off until its isolated assets/dependencies are installed and actual synthesis, listening quality and memory/analysis contention are measured. Keep voice-preserving conversion a separate experiment.
3. Treat offline Mandarin calibration as research until a legitimate dataset, trained model, held-out-speaker metrics and a separately approved live scoring design exist.
4. Review and approve scoped commits before sharing: (a) American guides + saved guidance preference/UI/contracts/tests; (b) offline Mandarin research modules/tests; (c) opt-in generation adapter/tests/setup; (d) integration evidence/report. Existing playback/speed/reliability work needs its own reviewed boundaries. No current work has been committed or pushed by this integration.

**Readiness:** ready locally with caveats for American guidance and private profile preference, with the established assessment speed retained in the executed sample. Optional Kokoro is connected but not installed/real-model-validated here; calibrated Mandarin grades and voice conversion are not complete features.
