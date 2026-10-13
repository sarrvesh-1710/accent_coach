# Generation integration examples

These fictional development envelopes match the keys and types in
`contracts/examples/job_accepted.json` and `job_failed.json`. Identifiers are
illustrative, not playable recordings or authenticated sessions.

Submission returns queued status; completion is read from the authorized session's
`jobs.example_generation`. On success, link an asset with `type: synthetic_example`,
its opaque `audio_id` and matching `input_revision`. No raw disk paths are returned.

Failure includes a safe code, user-facing message and retryability. Keep the
analysis job and its findings intact when generation fails. Transcript confirmation,
revision conflict, BUSY, TIMEOUT, unsupported accent and unavailable session use
the same error envelope with the corresponding code.
