# Day 1 handoff: start here

October 12, 2026. Contract and four bounded milestone decisions approved by Sarrvesh. Application implementation remains Day 2 work.

## Read first

1. [Approved interface](TEAM_INTERFACE.md)
2. [Implementation design](FREE_SPEECH_DESIGN.md)
3. [Measured Day 1 report](DAY_1_ENGINEERING_REPORT.md) and [portable measurements](DAY_1_BENCHMARK.json)
4. [Fictional contract examples](../contracts/examples/README.md)

## Owners and next deliverables

- Sarrvesh: recognition-only function, confirmed-transcript analysis snapshot, word/phone occurrence indexing and MFA timing investigation. Coordinates app_2.py/pipeline.py.
- Lucas: server identity, create/read/update/delete attempts, immutable learner assets, confirm_transcript, atomic revision checks and private history/playback. Report auth/storage choice and any signature blocker before shared wiring.
- Parthiban: confirmed-text synthetic generation, distinct generated assets and revision-aware result publication. Report model/license/environment choice and measured first-generation timing. Voice-preserving conversion remains stretch work.

## Agreed constraints

Five seconds, 10 MB, 1–12 words and 200 characters; General American initially. TH versus S/T/F, IH versus IY, AE versus EH. Missing dictionary words block assessment preflight without an incorrect label. ASR disagreement/unavailability permits confirmed-text diagnostics but sound feedback stays inconclusive. Generated assets never substitute for learner input. No validated grade.

## Branch coordination

This handoff is published on feature/speed-free-speech. It does not implement free speech or merge into team/week1-foundation. Teammates can read these documents on GitHub immediately. Before integrating shared interface work, review this scoped handoff for promotion to the integration branch; do not blindly cherry-pick all of another feature branch. Do not force-push or change another teammate's branch.

## Check-in requests

Please each report: interface questions, missing dependencies, first deliverable, and blockers. Read-only review of this handoff does not require merging branches. Existing preset behavior must stay runnable throughout development.

Sarrvesh should share the branch/document links in the team's usual channel. No direct teammate messages have been sent by the assistant.
