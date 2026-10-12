# Week-one execution plan

## Day 1

- Everyone: run baseline app/tests, review TEAM_INTERFACE.md, confirm ownership and GitHub handles, and verify shared fixture hashes.
- Sarrvesh: time three identical short inputs cold and warm; save total and stage timings with hardware and model versions. Identify bottleneck before selecting server capacity. Map preset dependencies and design transcript confirmation.
- Parthiban: prove confirmed text -> playable labeled synthetic audio in an isolated module; record generation latency. Investigate one voice-preserving accent-conversion candidate's weights, hardware and license. Do not promise this stretch goal until tested.
- Lucas: design owner-scoped sessions and authentication; prove two development users cannot access each other's sessions. No home-grown password cryptography.
- End-of-day: compare one example response from each module against contracts/examples. These JSON files are temporary test inputs, not a working service.

## Days 2-3

Implement custom text and short free speech, generation/playback, and profiles/private storage independently. Use agreed development examples until dependencies are ready.

## Day 4: first integration

Sign in -> create session -> record -> confirm transcript -> assess supported sounds -> generate example -> replay saved session. Record incompatibilities early.

## Days 5-6

Add simple practice suggestions, error recovery and resource scheduling. Test same-input cold/warm timings and concurrent requests. Test unsupported words, wrong sentences, silence, transcript edits, cross-user access, deletion during jobs and generation failure. Independently label real recordings; report uncertainty and denominators.

## Day 7

Freeze tested commit, document setup and measured performance, rehearse demo and prepare fallback clips/screenshots. No last-minute model/dependency upgrades.

## Completion checks

- Speed: before/after numbers on the same clips and hardware; no unsupported latency promise.
- Input: custom sentences work without lesson_id; short free speech requires transcript confirmation; unsupported sounds are explicit.
- Generation: words match confirmed text, asset type is accurate, playback works, failure does not erase analysis.
- Profiles: user B cannot read/play/delete user A's attempt via direct requests; deletion cannot be undone by a late worker.
- Integrated: revisions reject stale outputs, originals remain separate from generated audio, inconclusive is not treated as a mistake.

## Getting started

From an existing clone with a clean working tree: `git fetch origin`, then `git switch --track origin/<your-feature-branch>` (or switch to the existing local branch). Follow docs/DEMO_RUNBOOK.md for setup. Models, MFA and local settings are not bundled in Git. Keep consented personal recordings under ignored data/ or runs/.
