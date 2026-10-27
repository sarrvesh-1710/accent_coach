# Day 2 Phase 2: independent transcription

Implemented locally on `feature/speed-free-speech`, October 13, 2026.
Baseline: `9e326b4d50c596faf777bb845dc0b2eacd72fe6a`.

## Scope and implementation

- `speech_content.transcribe_audio(audio, settings)` transcribes a trusted learner WAV path or the existing `(samples, sample_rate)` input without a lesson ID, prompt, or expected sentence.
- `speech_content.check_content(audio, prompt, settings)` remains the preset comparison wrapper. The existing pipeline call and its result fields remain intact. Matching, target-variant, and mismatch comparisons still use `compare_transcript`.
- `audio_io.inspect_audio_file` shares the existing file validation boundary with transcription. It checks headers and size before decoding without feeding DSP-prepared samples to Whisper. The maximum is five seconds and 10,485,760 bytes (the existing binary interpretation of 10 MB); stricter configured duration limits still apply.
- The existing scoring audio preparation, CPU inference, model/revision settings, processor arguments, generation arguments, and one-entry model cache are retained. No dependencies were installed or upgraded.
- No changes were made to MFA, generated audio, UI, `pipeline.py`, or teammate-owned storage/generation modules. These edits are within Sarrvesh's assigned modules.

## Internal result and contract boundary

The independent function returns `status` and `transcription_status` as `completed` or `failed`, nullable `recognized_text`, model ID/revision, diagnostic limitations, and an error object when needed. It does not create a session or asynchronous job.

Audio identity has two distinct fingerprints:

- `source_audio_sha256`: original file bytes; null for array input.
- `audio_sha256`: the existing prepared PCM16 fingerprint used by the preset wrapper.

Neither fingerprint is an authorization token or an opaque storage asset ID. `learner_audio_id` remains null at this internal boundary because the current path-based code has no authenticated asset registry. The future `submit_transcription` adapter must resolve the original learner asset through Lucas's storage API, enforce ownership and asset role, and bind the returned text/provenance to that asset ID and input revision. This phase does not implement that adapter or claim full session-contract compliance.

Internal failure codes include `INVALID_AUDIO`, `MODEL_UNAVAILABLE`, `TRANSCRIPTION_EMPTY`, and `TRANSCRIPTION_FAILED`. The latter two are stage-specific diagnostics, not additions to the approved public error-code list. Their public mapping should be coordinated when implementing the job adapter. Internal exception reasons must not be exposed as public messages; the error object supplies a separate user-facing message.

Disabled checking and operational failures still return `unavailable` through the preset wrapper. One intentional correction: blank recognition now fails with null recognized text instead of becoming an empty-text comparison. Oversized/overlong direct transcription inputs are also rejected before model loading.

## Verification actually executed

| Check | Actual outcome |
| --- | --- |
| Focused extraction tests | 11 passed, 19.960 seconds |
| Full existing-plus-new unittest suite | 91 tests executed, 90 passed, one skipped, 14.451 seconds |
| Real offline cached Whisper, old-versus-new preset wrapper | Exact result-dictionary equality for all three example clips |

The skipped test is the existing Windows symlink test. Existing test warnings about Starlette/httpx and event-loop cleanup remain. Test-suite durations are not pipeline benchmarks.

Focused tests cover independent recognition, original/prepared audio fingerprints, provenance, all three preset comparison outcomes, empty/error handling, unchanged preprocessing and inference arguments, loader cache reuse and revision invalidation, and invalid audio including exact size/duration boundaries.

Real-model checks used `openai/whisper-base.en`, revision `911407f4214e0e1d82085af863093ec0b66f9cd6`. The old wrapper was loaded from the baseline Git version and shared the unchanged cached loader with the new code:

| Example | Recognized text | Old/new preset result |
| --- | --- | --- |
| think | I think so. | Equal; match |
| ship | The ship is here. | Equal; match |
| bad_bed | That is a bad bed. | Equal; match |

These three synthetic fixtures establish equivalence only for those checked outputs. They do not establish universal equivalence or pronunciation accuracy. No new real MFA or browser end-to-end run was performed in this phase.

Local evidence: `runs/day2-phase2-focused.log`, `runs/day2-phase2-regression.log`, `runs/day2-phase2-real-parity.log`, and `runs/day2-phase2-real-parity.json`. The runs directory is ignored by Git.

## Reproduce tests

From the repository directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_transcription.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
```

## Next integration work

1. Bind transcription to authenticated learner asset IDs and input revisions through the approved job/storage adapters.
2. Add explicit transcript confirmation and stale-result rejection before custom/free-speech analysis.
3. Implement confirmed-text dictionary preflight and alignment integration in the later phase while retaining preset guards.

The extracted function is ready for those steps; the app has not yet gained the complete free-speech flow from this change alone.
