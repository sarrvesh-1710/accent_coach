# Day 4: MFA investigation and approved opt-in cache experiment

October 18, 2026. Branch feature/speed-free-speech, HEAD e7f57d9. Day 3's playback fix/tests/handoff remained byte-for-byte unchanged (before/after SHA-256 comparison). No staging, commits, pushes, installed-package edits, dependency installation or persistent setting changes.

## 1. Scope and approvals

Phase 2 initially inspected only source, installed MFA 3.3.7 and prior logs. The lead then explicitly approved one cProfile diagnostic run. After its results were available, the lead explicitly approved the targeted dictionary-cache implementation/experiment. The changes below belong to that additional approval, not unapproved Phase 2 work. Activation in the running application is not included.

## 2. Current request lifecycle

1. Authenticated recording attachment validates upload/content limits and expected revision, assigns an immutable learner asset, and queues transcription. PracticeJobs resolves an authorized job snapshot and writes its learner bytes to a private temporary working directory.
2. Analysis requires explicit confirmed text, learner asset role, attempt/job/revision identity, dictionary coverage and original-byte hash. It reuses saved recognition/provenance rather than transcribing again. ASR disagreement still causes conservative diagnostic-only sound feedback.
3. AnalysisService serializes requests in a reusable spawned Python 3.13 worker. Whisper and phoneme model caches survive subsequent requests in that worker. A 180-second deadline handles worker failure/timeout and kills its owned tree when necessary.
4. run_confirmed_attempt prepares another private copy and invokes align_audio. Preset run_attempt similarly calls align_audio after its own content check. Both keep original fingerprints and full timeline.
5. align_audio creates a unique mfa_* directory with corpus/clip.wav, corpus/clip.lab and a new aligned.TextGrid output. It acquires ~/.accent_coach/mfa.lock (120-second acquisition timeout). It then launches a fresh MFA process using Python 3.11 from the MFA environment. No shell is used.
6. MFA validates dependencies, initializes its model/dictionary/tokenizer, computes MFCCs/CMVN, constructs its aligner, aligns the supplied text and exports a TextGrid. The application checks process success, output presence, phone/word boundaries, ordering and audio identity before phoneme analysis and feedback.
7. The phoneme model/scorer and assessment safeguards produce supported/practice/inconclusive experimental evidence. Storage accepts results only if owner, active job, revision, text and learner asset still match.
8. CLI output goes to the request's mfa.log. MFA gets 120 seconds; timeout handling kills/waits for its owned process tree before lock release. Other exceptions yield unavailable alignment, not fabricated phones. Confirmed-job temporary directories are cleaned by their contexts; preset benchmark run artifacts remain for audit.

Representative exact argument structure (W is the unique absolute request directory):

```text
C:\Users\sarrv\anaconda3\envs\accent-coach-mfa\Scripts\mfa.exe
  align_one W\corpus\clip.wav W\corpus\clip.lab
  english_us_arpa english_us_arpa W\aligned.TextGrid
  --output_format long_textgrid --no_use_mp
  --temporary_directory W\temp
```

Working directory is inherited from the parent (repository root in the measured commands); --temporary_directory does not set cwd. Child-only PATH prefixes select the MFA environment, Scripts, Library/bin and Library/usr/bin; CONDA_PREFIX identifies that environment. Dictionary and acoustic archive resolve under ~/Documents/MFA/pretrained_models/dictionary/english_us_arpa.dict and acoustic/english_us_arpa.zip. No credentials are needed or included. Current global MFA clean is false; the app explicitly disables multiprocessing for align_one. Actual acoustic metadata reports GMM-HMM and language unknown, so this call uses SimpleTokenizer rather than loading an English spaCy tokenizer model.

## 3. Repeated work established from installed source/artifacts

- The installed package/version metadata is MFA 3.3.7; its environment is Python 3.11.16. This was checked without running an unrelated version's CLI.
- command_line/align_one.py constructs a new AcousticModel and KalpyAligner each CLI invocation. models.py removes/reextracts its shared acoustic directory for an archive source. The global file lock remains necessary.
- Dictionary files live under config.TEMPORARY_DIRECTORY/extracted_models/dictionary/<dictionary-stem>. The code loads them if L.fst exists and clean is false; otherwise it parses the full dictionary and builds/writes the FSTs.
- Our original --temporary_directory is unique each request. Two retained baseline runs each wrote L.fst (47,681,534 bytes), L_align.fst (59,366,046), words.txt (3,024,462) and phones.txt (586): 110,072,628 bytes total per request. All four corresponding SHA-256 hashes match across those runs.
- align_one also runs third-party executable checks, some through short --help subprocesses. --no_use_mp does not make the entire request initialization-free.
- New audio features, transcript graph and alignment must still be computed for a new recording. There is no result reuse in the baseline.
- Repeated audio preparation/copying exists across boundaries, but its observed wrapper preparation cost is milliseconds; it is not the demonstrated dominant cost. Validation/fingerprint checks must not be removed casually.

Installed MFA's `server` CLI manages database servers; it is not a persistent alignment RPC service. Lower-level AcousticModel/LexiconCompiler/KalpyAligner objects and online functions exist, but no tested ready-to-use application alignment service was found. Reusing those objects would require a separate initialized MFA-environment worker/IPC and recovery lifecycle, not simply enabling `mfa server`. That is larger than this selected change.

## 4. Measured versus unmeasured costs

Phase 1's unaffected warm subprocess times: 18.988-20.514 s, about 94.4% of corresponding outer totals. Wrapper preparation ~3-6 ms; output handling ~1-20 ms for unaffected calls. Lock waiting ~0.259-1.772 ms across unaffected fresh/repeated calls. Those timers cannot split MFA internals. Existing retained mfa.log files were empty. Standby-affected calls are excluded.

Approved diagnostic: existing think fixture, same settings/lock and fresh output, direct MFA-environment Python executing the installed mfa-script.py through built-in cProfile. Process returned 0; diagnostic outer subprocess time 27.245 s. This is NOT an unprofiled speed baseline. Parsed TextGrid tiers and prepared-audio identity exactly match the same-clip Phase 1 result.

| Profile entry | Cumulative seconds | Meaning/limit |
| --- | ---: | --- |
| Initial MFA package import | 4.817 | Includes nested imports; not pure OS process startup |
| load_pronunciations | 3.378 | Full dictionary loading/parsing |
| create_fsts | 11.659 | Dictionary graph construction; includes its child calls |
| AcousticModel constructor | .470 | Includes .458 s archive unpacking |
| check_third_party | .815 | Dependency-check work including child commands |
| generate_mfccs | 3.001 | Everything under feature-generation call, including lazy work |
| KalpyAligner constructor | .452 | Graph/decoder initialization |
| KalpyAligner.align_utterance | .159 | Includes graph/feature/decoder work for this utterance |
| CMVN computation | .000768 | This fixture/profile only |
| TextGrid export | .001243 | This fixture/profile only |

Cumulative profile entries can overlap; do not add rows into a process budget. Profiling adds overhead. Pure OS/Python startup, universal per-stage costs and whole-browser latency remain unmeasured. No speed saving was inferred by subtracting profile entries.

Diagnostic evidence: runs/day4-mfa-profile-20261018T192328Z/{diagnostic.json,mfa.pstats,aligned.TextGrid,mfa.log}. Normal MFA runtime side effects, including shared model extraction/history, still occurred; application/installed source and configuration were not edited by profiling.

## 5. Selected minimal optimization and implementation

Reuse compiled dictionary resources, not utterance alignments. This can benefit a genuinely different recording using the same resources. Exact-input result caching is a separate retry-only idea and was not implemented.

Opt-in internal setting: mfa.dictionary_cache_directory must be an absolute server-controlled path. It is absent from persistent settings, so normal application behavior remains unchanged. The experiment supports only direct Windows MFA 3.3.7; unsupported installations bypass it.

- Key includes dictionary/acoustic content hashes, runtime/environment identity, relevant Conda metadata, MFA global config/profile and effective MFA settings. No learner data is part of the cached resource set.
- Under the existing lock, validate hashes of all four completed cached files, copy them into a staged folder in the fresh request's temporary directory, then atomically expose that folder. No hardlinks/shared mutable FST files.
- On hit only, add --no_clean to use MFA's existing load branch. Audio, transcript and TextGrid directories remain unique. Model/decoder settings, evidence rules, locks and deadlines remain unchanged.
- Publish new resources atomically only after successful process/output checks. Cache contains the four files and integrity manifest, never WAVs, transcripts, TextGrids or sound findings.
- Missing/corrupt/incomplete cache or setup/copy/publication errors fall back to normal compilation where possible. Corrupt existing entries are retained for review rather than deleted automatically. A runtime MFA loading failure remains an alignment failure; no silent second 120-second attempt is added.
- About 110 MB shared disk storage plus per-request copies; models still initialize per CLI call. This is not a persistent in-memory aligner and is not zero-startup work.

Code: phoneme_scoring/mfa_dictionary_cache.py and a guarded hook in align_audio.py. Focused tests: tests/test_mfa_dictionary_cache.py and additions to tests/test_mfa_timings.py. No app/auth/storage/UI interfaces changed; the additive internal dictionary_cache diagnostic is not a new public session schema.

## 6. Unprofiled real alignment experiment

Same installed resources, complete transcripts, lock, flags and timeouts; one process per call and unique input/output directories. Enabled settings supplied only in memory; cache directory under the ignored experiment folder. All are engineering fixtures, not accuracy labels. No competing project analysis tests ran during these calls; no standby event was recorded during the experiment. Background load uncontrolled and order fixed, with only one baseline/hit pair per clip.

| Order | Clip | Condition | MFA subprocess s | Whole alignment s |
| --- | --- | --- | ---: | ---: |
| 1 | think | Disabled baseline | 27.714 | 27.722 |
| 2 | think | First build/miss | 24.958 | 25.573 |
| 3 | ship | Resource hit, different recording | 9.659 | 10.248 |
| 4 | ship | Disabled baseline | 26.593 | 26.602 |
| 5 | bad_bed | Disabled baseline | 24.984 | 24.994 |
| 6 | bad_bed | Resource hit, different recording | 10.096 | 10.658 |
| 7 | think | Resource hit | 9.094 | 9.700 |

All seven calls returned available. For each clip, every enabled result exactly matched its disabled baseline's parsed phone/word segments, boundary corrections, prepared-audio identity, duration and sample rate. Original input is never substituted by cache contents. Seed/publish overhead is included in whole alignment time, outside the existing subprocess timer.

Median disabled total 26.602 s; median hit total 10.248 s: descriptive 61.5% reduction in this small alignment-only experiment. Do not claim whole-app, first-ever request, five-second human speech or production improvement from it. The miss still compiles; its difference from baseline is not a cache-hit gain.

Evidence: runs/day4-dictionary-cache-20261018T192902Z/measurements.json and numbered result JSONs. No profiler used in these comparisons.

## 7. Verification and next gate

Focused command `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_mfa*.py' -v`: 14 passed. Covers invalidation, resource-only content, independent copies, atomic publication/seed, corruption/copy failure, unsupported runtime fallback, lock/timing/argument boundaries, publication failure and timeout nonpublication.

Full regression command `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v`: 165 tests, 164 passed, one existing Windows symlink skip, zero failures, 35.549 seconds. Evidence: runs/day4-dictionary-cache-tests.log. This includes the Day 3 renderer wrapper (10 JavaScript scenarios), preset/free-text tests and real SQLite/auth/revision tests with controlled engines. It does not replace new human recordings or end-to-end timing with cache activation. Existing dependency/deprecation/event-loop warnings remain. `git diff --check` passed; no dependency or persistent settings changes.

Fallback is the unchanged disabled path: remove/omit the experimental option. Before activation, obtain explicit approval for any local configuration change, run confirmed-text and preset end-to-end comparisons, test a second server/worker under the same lock, cache invalidation and failure recovery, and obtain more varied unprofiled samples. Keep existing role/identity, ownership, revision and conservative-evidence tests passing. The Day 3 playback change is separate and remains uncommitted. No code was staged or pushed.

## 8. Phase 3 implementation recheck

The cache implementation above already existed from the explicit experiment approval. This phase reviewed it rather than adding another optimization. Review found that syntactically valid non-object JSON manifests (for example, a list) raised AttributeError instead of falling back. The expanded corruption test reproduced that failure before the fix. The helper now checks the manifest and files mapping types before using them; invalid shapes return a cache miss and leave compilation to the existing MFA path. No alignment settings or public interfaces changed.

Rerun commands and observed results:

- `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_mfa*.py' -v`: all 14 passed. Resource tests use real temporary filesystem artifacts; MFA subprocess/clock tests use controlled test doubles, not model inference.
- `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v`: 165 tests, 164 passed, one Windows symlink skip, zero failures, 32.636 seconds. Log: runs/day4-phase3-verification.log. Existing dependency/resource warnings remain. These regressions include preset behavior, transcript preparation, identity/revision and stale-job handling, conservative evidence and learner/generated separation with controlled analysis components. They are not a new real-model or browser acceptance run.
- `git diff --check`: passed. Index remains empty. Day 3 playback implementation, both playback test files and the Day 3 handoff retain their previously recorded SHA-256 hashes.

The persistent settings still omit dictionary_cache_directory. No service was started/restarted or configuration activated in this recheck, and no additional performance measurements were made. The earlier seven real-MFA calls remain limited alignment-only experiment evidence; Phase 4 must establish comparable full-pipeline behavior and timings before any whole-app speed claim. No model preparation before the first request was introduced. Missing/corrupt cache falls back to normal compilation, publication failure preserves a successful alignment, and an MFA runtime failure/timeout follows existing unavailable/error handling rather than adding a second attempt.
