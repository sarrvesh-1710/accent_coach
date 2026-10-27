# Approved interface examples

Fictional payloads for the flat contract in `docs/TEAM_INTERFACE.md`; no API implementation, inference, timing or real user data is implied.

- `session.json`: confirmed input at revision 2 after transcription; analysis and generation have not been requested, so their statuses are null. Empty sound results are not a perfect score. Timings are omitted because no measurements exist.
- `job_accepted.json`: example analysis job receipt for revision 2.
- `job_failed.json`: independent generation failure envelope for revision 2; a failed generation does not invalidate analysis.

Lifecycle values are queued, processing, completed, failed and cancelled. Sound outcomes are supported, practice and inconclusive. The old nested jobs/generated_assets format and not_requested status are no longer used.

Do not deploy fake-user authentication to use fixtures. Server identity, ownership, audio roles and revision checks must be implemented separately.
