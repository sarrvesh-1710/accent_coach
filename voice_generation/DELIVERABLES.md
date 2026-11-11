# Parthiban: Day 1â€“2 deliverables and integration handoff

Scope: Parthiban's generation/playback responsibilities in the
[week-one plan](../docs/WEEK_ONE_PLAN.md) and
[team interface](../docs/TEAM_INTERFACE.md). This is a local development component;
production accounts, persistent private storage and main practice-page wiring are
the later team integration milestone.

## Day 1 â€” complete

- Isolated Python environment and dependency lock for generation; shared model
  dependencies are unchanged.
- Callable text + target accent -> labeled, playable synthetic audio.
- Three reviewed examples: short, longer, practice sounds; 12 measured Kokoro
  trials, each sentence once cold plus three warm repeats.
- Word matching reviewed by Parth for all three examples. Naturalness ratings:
  short 4/5, longer 4/5, practice sounds 3/5. Short/longer accent suitability was
  rated suitable; practice-sounds accent suitability was not separately rated.
  Parth subsequently confirmed TH/IH/AE sound good. These are one listener's
  observations, not validated pronunciation accuracy.
- Conversion candidate, public weights, hardware and licensing investigated in
  [FEASIBILITY.md](FEASIBILITY.md). Voice preservation remains unproven; working
  conversion is not required for Day 1.

Warm request medians: short 1.972 s; longer 5.935 s; practice sounds 1.728 s.
Cold totals: 28.921 s, 21.531 s, 48.481 s respectively. Downloads are excluded.
The final sentence was resumed after the laptop restart, so these are initial
observations under different startup conditions, not a controlled cold comparison.
Hardware, model revision, every trial and timing boundaries are in the saved JSON.

## Day 2 â€” complete

- Self-contained **Hear an example** component at http://127.0.0.1:8762/.
- Confirmed custom text, target-accent label and **Synthetic example** playback.
- Queued/processing/completed/failed states, failure messages and retry.
- One model worker reused between calls; one active generation at a time and a
  120-second deadline including startup.
- Input edits clear playback and require confirmation; revisions reject stale
  outputs. Deletion makes a session unavailable before cleaning generated assets.
- Generation failure preserves independent completed pronunciation feedback.
- Generated audio remains separate from learner recordings and assessment input.
- Twelve Day 2 service/HTTP/timeout checks and six generation checks passed.
  Shared fixture hashes and isolated dependency consistency passed. The full shared baseline suite ran 98 tests: 97 passed and one symlink check was skipped because this Windows installation cannot create symlinks.
- Two real queued jobs completed with authorized playable WAV output: cold job
  12.602 s and subsequent warm job 1.252 s. Browser checks confirmed loading,
  completion, playback and clearing stale audio after a text edit. Parth reported
  the demo's manual checks work.

Launch and usage: [DAY2_RUNBOOK.md](DAY2_RUNBOOK.md).
Benchmark/review method: [KOKORO_RUNBOOK.md](KOKORO_RUNBOOK.md).

## Supplied generation interface

`generate_example(auth_context, attempt_id, input_revision)` returns the agreed
queued envelope. It obtains confirmed text/accent from authorized storage, not
browser-provided ownership or unrestricted paths. Consumers poll the session's
`jobs.example_generation` and `generated_assets`. Illustrative development
success/failure payloads are in `examples/`; they are not real learner results.

`DevelopmentStore` is a temporary localhost adapter. Lucas's real adapter must
preserve atomic owner, current revision, current job and deletion checks for
result acceptance, plus authorized playback and deletion. The fixture tests are
not evidence of deployed multi-user authentication.

## Day 3 handoff / Day 4 integration

- Sarrvesh: wire confirmed transcript controls and mount the panel beside learner
  playback; keep generation and analysis statuses independent.
- Lucas: supply authorized snapshots, persistent job/asset storage and playback
  routes, with owner/revision/deletion checks.
- All three: compare the supplied responses with `contracts/examples`, agree on
  the adapter boundary and choose resource scheduling based on timings.
- Keep Kokoro in its isolated environment: its Transformers version differs from
  the shared assessment environment. Do not import it into the shared app directly.

These teammate coordination items have not been represented as completed. No
shared app, pipeline, account or contract files were modified for this component.

## Evidence handoff

`runs/parthiban_day1_day2_deliverables.zip` contains the three reviewed synthetic
WAVs, their metadata, audio-ID mapping, the complete benchmark measurements,
listening review, real-service smoke results, relevant runbooks and feasibility
note. Model weights, virtual environments and learner recordings are excluded.
The evidence ZIP and runtime recordings are ignored by Git; share the ZIP
separately. Source code, runbooks and this checklist can be committed normally.
