# Day 2: Hear an example component

From the repository root, use the isolated generation environment:

```powershell
.\voice_generation\.venv\Scripts\python.exe -m voice_generation.demo
```

Open http://127.0.0.1:8762/. Enter or edit text, confirm it, then press
**Generate example**. The first call loads Kokoro; subsequent calls reuse the
same model process. The audio is labeled **Synthetic example** with a General
American target label. Loading, failure and retry states are separate from analysis.
Generation time is shown after completion. Editing text clears playback immediately
and requires new confirmation. Confirming increments the input revision, invalidates
dependent results and removes old generated files. Deleting the demo session makes
it unavailable before clearing assets. Late results are rejected and cleaned up.

Keep the terminal running; Ctrl+C stops the demo and its model process. A session is
in memory for this server lifetime. Reloading the page preserves that session;
restart the server to create a fresh one after deletion. Generated audio is under
ignored `runs/day2_examples/`. It never enters the learner assessment pipeline.

## Interface supplied to teammates

`GenerationService.generate_example(auth_context, attempt_id, input_revision)`
loads the authorized, confirmed text and target accent from storage. Submission
returns the queued response envelope from TEAM_INTERFACE.md; clients poll the
session's independent example_generation job record. Successful assets use opaque
IDs and `synthetic_example` type. Playback invokes authorization again.

`DevelopmentStore` is an explicitly local test adapter derived from
`contracts/examples/session.json`, not production authentication or persistent
storage. Replace it with Lucas's adapter preserving atomic owner/revision/job/deletion
checks. No user identity or raw disk path is accepted from the browser as authority.
The demo binds only to localhost and validates request hosts and mutation tokens.

`ModelWorker` runs Kokoro in one isolated process, accepts one generation at a time,
reuses weights, and terminates/restarts a hung or failed worker. The default deadline
is 120 seconds including startup. Failed generation never overwrites analysis.
Superseded jobs may finish their inference; their outputs are discarded rather
than attached to the changed/deleted session.

The playback UI is in `voice_generation/panel/`, using feature-specific styles.
No shared practice-page, pipeline, dependency or session-contract files are changed.
This is a component demo, not the main practice page at port 7861.

## Checks

```powershell
.\voice_generation\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_example_*.py' -v
```

Checks cover transcript confirmation, queued/completed envelopes, reusable backend,
generation failure with retained analysis, retry, stale revisions, edits/deletion
during inference, old playback removal, unsupported accents, BUSY and cross-user
access. Software fixture tests are not pronunciation validation.

Manual check: confirm **I think so**, generate and play; generate another sentence
to observe warm loading; edit text while generating and confirm again; verify the
old output never appears. Delete the session during processing and verify no audio
can be played afterward. General American suitability remains listener-reviewed.

## Day 4 wiring

Coordinate with Sarrvesh to mount the panel beside learner playback and confirmed
transcript controls. Coordinate with Lucas for authorized storage and asset routes.
Keep model dependencies in this environment; the shared app's Transformers version
differs from Kokoro's pinned version. Use a small local API/worker boundary rather
than importing Kokoro into the shared scoring environment. Production deployment,
accounts, durable storage and cancellation scheduling require that team integration.
