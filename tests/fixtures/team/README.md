# Shared software fixtures

Paths in manifest.json are relative to the repository root. The speech assets reuse bundled Microsoft Zira synthetic listening examples. Their manifest is in web_assets/examples/manifest.json. Silence and seeded low-amplitude random noise are generated controls: two seconds, mono PCM16, 16 kHz, seed 403. No personal recording is included. Synthetic speech is not a human pronunciation label and must not be used to advertise accuracy.

Use the same file hashes when comparing speed. Record Git commit, model version, hardware, cold/warm state, selected lesson/text, stage times, total time and observed outcome. Do not assume a particular model result just because a clip is synthetic. The wrong-sentence control uses ship.wav with the think prompt.

## Human examples still required

Record with each speaker's permission and store locally under ignored data/evaluation/:
- Clear expected target (think, ship, bad).
- Deliberately altered target (sink/fink, sheep, bed); independent listeners label the actual sound, not the recording instruction.
- A natural custom sentence containing a supported sound.
- An unfamiliar name or unsupported word, with confirmed spelling.
- A realistic noisy sample and natural pace variations.

Use docs/VALIDATION_PROTOCOL.md for labels and speaker splits. Do not commit these recordings without explicit agreement from the recorded speakers. The team still needs to collect/review them; this setup does not claim completed human evaluation.

## Integration scenarios without speech fixtures

Use fictional users A/B to test access rejection. Change transcript mid-job to test stale revision rejection. Fail example generation while analysis succeeds. Delete a disposable development attempt mid-job and verify no late result recreates it. Lucas should implement these as real authorization/storage tests, not just UI checks.
