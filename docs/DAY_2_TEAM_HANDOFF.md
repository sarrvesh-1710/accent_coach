# Day 2 handoff: speed and free-speech foundations

October 13, 2026. Owner: Sarrvesh. Review against `TEAM_INTERFACE.md`, `FREE_SPEECH_DESIGN.md`, contract examples and `FILE_OWNERSHIP.md`.

**Outcome:** independent transcription, conservative text preparation, a confirmed-text analysis worker and MFA timing instrumentation are implemented and verified locally. Full free-speech UI, authenticated storage and public job submission remain incomplete. No performance optimization, validated grade, production security or complete multiuser integration is claimed.

## 1. Git and environment

- Day 2 starting state, established in Phase 1: clean `feature/speed-free-speech`, HEAD `9e326b4d50c596faf777bb845dc0b2eacd72fe6a`, synchronized with origin. Agreed application baseline remains `2a3352f`.
- Phase 6 started with four tracked modifications and eleven untracked Phase 2–5 source/test/report files; index empty.
- Ending state: same branch and HEAD, four tracked modifications and thirteen untracked files, including this report and the reproducible smoke tool. No files staged, committed, pushed, discarded or merged. Origin's speed branch still matches HEAD (zero commits ahead/behind).
- Windows 11, shared Python 3.13.1 virtual environment, CPU models, MFA 3.3.7 in the existing `accent-coach-mfa` Conda environment. Models use installed pinned caches; smoke inference ran offline. No packages installed/upgraded or settings/dictionaries changed.
- `git diff --check` passed. Git emits ordinary LF-to-CRLF notices. `git diff --stat` shows tracked edits only; new modules/tests/docs are untracked and must be included explicitly in approved commits.

## 2. Completed foundations

**Independent transcription:** `speech_content.transcribe_audio(audio, settings)` requires no lesson ID. Returns nullable recognized text, original-file/prepared-audio fingerprints, status and model provenance. Empty/failed recognition is explicitly failed. `check_content` preserves the preset match/target-variant/mismatch wrapper. `learner_audio_id` remains null internally until authenticated storage binds the original asset; a hash is not an asset ID or authorization token.

**Transcript preparation:** `transcript_input.prepare_transcript` enforces 1–12 normalized words and 200 original Unicode code points. Contractions count as one word. Supported sentence punctuation separates tokens; capitalization and right-curly apostrophes normalize consistently. Unsupported symbols/digits/hyphens/non-English letters fail explicitly. Original text, token spelling, source offsets and zero-based indices are retained. Lookup uses the configured installed MFA dictionary, reports its hash, lists missing occurrences without grading them, and does not invent pronunciations. Word/phone occurrence identities distinguish repetitions and pronunciation candidates.

**Confirmed-text worker:** `confirmed_analysis.run_confirmed_attempt` consumes a trusted confirmed-text/learner-asset/attempt/job/revision snapshot. It reuses current audio preparation, MFA, scoring and assessment safeguards without preset lookup. Ordered aligned words must match prepared tokens; occurrence targets use segment IDs. Outputs are supported/practice/inconclusive experimental evidence, never validated errors or grades. ASR disagreement or missing matching audio provenance withholds sound judgments. Generated asset roles and changed original-file hashes are rejected.

**Publication seam:** `execute_confirmed_analysis` resolves input through an authorized store boundary and publishes only through atomic owner/job/revision/text/asset checks. Stale rejection is tested with a clearly labeled fake store. This internal protocol is proposed for Lucas's adapter; it is not a production authentication implementation or the approved asynchronous `submit_analysis` API.

**MFA instrumentation:** additive monotonic timings separate lock acquisition, subprocess execution, preparation, output processing and total elapsed time. Original arguments, timeout/cleanup, lock, fresh directories and installed-model caching are retained.

## 3. Phase 6 tests actually executed

Run all commands from the repository directory. The command prefix below is literal:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_transcription.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_transcript_input.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_confirmed_analysis.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_mfa_timings.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_assessment.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_pipeline.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_reference_free.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_release_features.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe -B tools/verify_day2_smoke.py
```

| Group / command pattern | Actual result | Components and limits |
| --- | --- | --- |
| test_transcription.py | 11 passed | Real WAV preparation; mocked Whisper/model loading. Checks independent input, identities/provenance, inference arguments/cache keys, empty/failure handling, preset checks and recording limits. |
| test_transcript_input.py | 12 passed | Unit/file integration with fixture dictionaries. Limits, contractions, offsets, unsupported/missing words, stable repeated identities and dictionary errors. |
| test_confirmed_analysis.py | 13 passed | Real audio/text/validators/assessment and sequence arithmetic; mocked MFA/scorer; fake store. Checks confirmation, identities/revisions, stale edits/retries/deletion/ownership, generated role rejection and abstention. |
| test_mfa_timings.py | 4 passed | Fake elapsed clock/process; exact lock/subprocess/total boundaries, lock failure, timeout and executable failure. |
| test_assessment.py | 11 passed | Real arithmetic and safeguard logic; no accuracy labels or real model inference. Preset content checks and uncertain-result abstention. |
| test_pipeline.py | 22 passed | Real DSP/file integration and Gradio construction; mocked speech/alignment/scoring components. Preset and reference-free regressions. |
| test_reference_free.py | 5 passed | Boundary association, operational-result checks and UI construction; no production storage. |
| test_release_features.py | 10 passed, 1 skipped | Includes real cross-process lock exclusion, owned-process timeout cleanup/recovery, catalog and worker tests. Symlink test skipped because this Windows installation cannot create symlinks. |
| Full test_*.py suite | 119 passed, 1 skipped, zero failures | 120 tests in 19.692 seconds. Overlaps the groups above; do not add their counts to this total. |
| verify_day2_smoke.py | 6 checks passed, zero skips | Real cached models and MFA; existing local demo recording; trusted worker fixture only. Details below. |

Existing Starlette/httpx deprecation and unclosed-event-loop warnings remain. Whisper also emits the existing max_new_tokens/max_length precedence warning; generation settings were not changed. An initial Phase 5 test-helper naming conflict was corrected before its final tests; no final verification failures remain.

Evidence lives under ignored `runs/day2-phase6/`: per-group logs, `verification.json`, `real-smoke.log`, and `real-smoke.json`. The real preset result was saved under the normal ignored runs history. No private/raw audio artifacts are proposed for Git.

## 4. Real-model evidence and regressions

The smoke used the existing local demo recording `data/references/think.wav` as a controlled test input, with reference comparison disabled. No synthetic listening example was declared an original learner asset. This is not a reviewed accuracy sample or a real persisted user session.

1. Independent Whisper transcription completed with original/prepared hashes and pinned model provenance.
2. Old `HEAD` and new preset wrapper returned exactly equal dictionaries for this clip: match.
3. Real preset pipeline completed its operational path, with MFA available and phoneme model revision present. Overall status remained honestly partial because some pronunciation evidence was uncertain.
4. Old `HEAD` and instrumented MFA produced equal status, phone segments, word segments, audio identity, duration, sample rate and boundary corrections for this clip. This supports equivalence of these checked outputs, not every possible recording.
5. Real confirmed-text worker completed with no lesson lookup: TH was inconclusive and IH supported under the experimental rule. Fixture attempt/job/revision/audio identity was retained. No real store/publication/browser was exercised.
6. Changing the fixture asset role to synthetic_example returned INVALID_AUDIO before assessment.

ASR loader AST comparison with HEAD was identical. Focused tests verified unchanged CPU placement, model/revision/cache arguments, deterministic generation arguments and existing preparation samples. The one-entry model cache still reuses an identical key and reloads for revision changes.

The catalog's 12 presets pass configuration/regression checks; one preset's full real pipeline was rerun in Phase 6. Earlier Phase 2 real wrapper checks covered all three core recordings, and Phase 5 real MFA measurements covered all three core synthetic fixtures. This does not establish full real-model coverage of every preset.

Limits are five seconds and 10,485,760 bytes (the existing binary interpretation of 10 MB); exact-duration/size boundaries are tested. The five-second ceiling is now enforced even if a direct caller configures a longer limit. Blank transcription becoming failed rather than an empty comparison is an intentional correction.

## 5. Actual MFA timing findings

Phase 5 command: `.\.venv\Scripts\python.exe -B tools/benchmark_mfa.py`.

Ten real calls succeeded, no retries: three clips in three serial rounds, then one controlled contention call. Each launched a fresh MFA subprocess through Conda; installed caches were not cleared and output directories were fresh. The first think call overlapped test completion and is excluded from clean statistics.

| Clip | Clean n | Median total (s) | Subprocess min–max (s) |
| --- | ---: | ---: | ---: |
| think | 2 | 32.074 | 25.955–38.167 |
| ship | 3 | 24.040 | 23.474–26.731 |
| bad_bed | 3 | 28.878 | 25.179–52.746 |

Clean lock waits: 0.245–0.651 ms. Subprocess execution consumed 99.95% of clean alignment-operation time. Controlled contention measured 2.009 s lock wait, 21.701 s execution and 23.720 s total. It demonstrates the timing boundary, not typical production contention.

Preparation and output parsing were milliseconds. Empty MFA console logs gave no reliable startup/model-loading/feature/decoding breakdown. Cold-start/cache/background-load effects cannot be isolated; the 52.746-second outlier remains in the report. No optimization succeeded or speed improvement was demonstrated. All ten rows and exact boundaries are in `DAY_2_PHASE_5.md`; raw JSON is under ignored runs.

## 6. Incomplete work and integration review findings

- Public submit_transcription/submit_analysis, confirmation UI, authenticated original learner asset resolution, persistent job/revision state, atomic publication and real-store race tests remain unwired. Internal worker results are not complete flat session snapshots.
- Reused ASR model provenance is required but currently only checked for presence in the worker. Before public integration, enforce compatibility with configured model/preprocessing identity and test old-revision reuse rejection.
- Worker processing_ms currently updates through its last timed stage, excluding final assessment/result formatting and cleanup. Finalize total processing measurement before relying on the public timing field; do not compare it directly with whole-browser latency.
- Dictionary preflight is ARPA/English-specific and mirrors the current local MFA root. Remote/custom MFA wrappers may need explicit dictionary resolution. Contraction splitting/merging in real MFA requires more smoke cases; mismatches abstain rather than guess.
- The generated-role guard relies on trustworthy server asset classification. Existing legacy local paths and history are not a secure public asset registry. Real owner/deletion/revision guarantees cannot be inferred from the fake store.
- No unrelated UI, pipeline entry-point, shared settings, dictionary, dependency or model-weight modifications were found in Sarrvesh's local diff. No broad refactor was undertaken in Phase 6.

### New teammate work discovered by fetch

Lucas: origin/feature/profiles-personalization now at `76cef88`. It supplies `accent_profiles_integrated.patch`, not applied source modules on this checkout. Read-only `git apply --check` passed against the current working tree; this establishes textual applicability only. The patch adds accounts/storage and changes app_2.py, pipeline.py, analysis_service.py, site_server.py, site_pages.py, README, dependencies and assets. It contains no input_revision field and still creates preset-based attempts. Owner/deletion checks are present, but confirmed-text job/asset/revision publication needs reconciliation. His tests were inspected but not executed here; do not treat his patch's claims as verified integration.

Parthiban: origin/feature/voice-conversion now at `09f6de1`, with isolated voice_generation source and tests. Its target accent matches. The development API uses generate_example, nested jobs/generated_assets, not_requested state and a 1,000-character input cap; the shared contract specifies submit_generation, flat nullable job fields and the 200-character/12-word practice scope. Map these boundaries and enforce shared preflight before integration. Preserve its isolated environment and synthetic_example labeling. His generation tests/benchmarks were not rerun in this checkout. Neither teammate branch was merged or modified.

## 7. Git review and proposed scoped commits

Four tracked modifications: `audio_io.py`, `speech_content.py`, `phoneme_scoring/sequence_evidence.py`, `phoneme_scoring/align_audio.py`. Thirteen untracked files are explicitly covered below. Tests and reports exist but will be absent from tracked-only diffs until approved staging.

| Proposed commit | Exact files |
| --- | --- |
| Extract independent transcription and validate recording limits | audio_io.py; speech_content.py; tests/test_transcription.py; docs/DAY_2_PHASE_2.md |
| Prepare confirmed English text and dictionary occurrence identities | transcript_input.py; tests/test_transcript_input.py; docs/DAY_2_PHASE_3.md |
| Add confirmed-text analysis worker and guarded publication seam | confirmed_analysis.py; phoneme_scoring/sequence_evidence.py; tests/test_confirmed_analysis.py; docs/DAY_2_PHASE_4.md |
| Instrument MFA lock and subprocess elapsed time | phoneme_scoring/align_audio.py; tests/test_mfa_timings.py; tools/benchmark_mfa.py; docs/DAY_2_PHASE_5.md |
| Verify Day 2 components and publish engineering handoff | tools/verify_day2_smoke.py; docs/DAY_2_TEAM_HANDOFF.md |

Ordering reflects dependencies. Commit 3's storage protocol and occurrence selector require integration review with Lucas; added timing/result fields also need consumer awareness. Lucas's shared-file patch must be integrated in a separate reviewed change, not silently staged with these commits. Keep logs, patches copied for inspection, local recordings, models and virtual environments out of staging.

**Approval required before staging/committing these five scopes.** Nothing has been staged or committed as part of this handoff. Publishing/pushing is a separate action.

## 8. Recommended next actions

1. Coordinate Lucas's profile patch and Parthiban's development service around the approved flat session schema, shared limits, original/generated asset roles and atomic owner/job/revision checks. Agree adapter signatures and test them against real storage before wiring UI.
2. Complete recognition-provenance compatibility checks and total worker timing, then add explicit transcript confirmation and revision-aware public submission while preserving presets. Verify actual repeated-word/contraction/custom-sentence recordings and late-result races.
3. Run a controlled direct-MFA-environment versus Conda-launcher experiment with identical inputs, locks, timeouts and output checks. Subprocess time dominates, but its startup share is unknown. Adopt an optimization only after measured improvement and behavior parity.

Human consented recordings, independent sound labels and held-out evaluation are still required to assess pronunciation reliability. These engineering checks establish operation and safeguards, not a validated accent grade.

## 9. Approval after verification

The project lead approved the five scoped commits after receiving this handoff. The Git-state and approval statements above record the pre-commit verification snapshot. The approved source commits are:

- `706292b`: independent transcription and recording limits.
- `9828127`: transcript preparation and dictionary occurrence identities.
- `bdabbea`: confirmed-text worker and guarded publication seam.
- `cece3cd`: MFA timing instrumentation.

The fifth commit contains this handoff and `tools/verify_day2_smoke.py`; obtain its final ID from `git log -5 --oneline`. No source behavior changed after the reported verification. Commit approval did not authorize pushing or merging.
