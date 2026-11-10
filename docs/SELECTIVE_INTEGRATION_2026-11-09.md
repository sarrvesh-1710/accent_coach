# Selective integration, November 9, 2026

Base: feature/speed-free-speech at 529e28e. Adapted Parthiban profile-system at ea52da5.

Added microphone level and quiet/loud feedback, local WAV playback before upload, record-again/discard, and controlled microphone cleanup. Capture stays local until save. Existing preset, custom-text and free-speech submission paths remain.

Added authenticated starting checks and saved personalized sentence sequences. Recommendations use recent sound findings and selected goals. Completed inconclusive processing earns practice credit, not mastery; failed processing does not advance. Old attempts do not fill a newly started plan. Restart preserves History. Added progress and plan sections on Profile and Practice. Existing profile preferences remain compatible.

Database tables are additive and initialized through existing Store startup. Tests use temporary databases; existing private account data was not edited during implementation.

MFA implementation, model settings, transcription/revision safeguards and generation adapters are unchanged. Kokoro remains optional. No new speech model imports or periodic lesson-plan polling were added. Plan refresh uses page load/focus/completion.

Verification: see output/integration-tests-20261109-final.log. Focused lesson-plan 13/13, coaching 7/7 and playback wrapper passed; controlled microphone component 11/11. These are unit, controlled DOM/lifecycle and temporary HTTP/SQLite integration tests. They are not live human microphone acceptance or performance measurements.

Next: launch/restart app with .\.venv\Scripts\python.exe app_2.py, sign in, try starting check, record/review/discard/save, complete a preset analysis, verify plan progress and original playback in History. Retest warm timing under the same power/memory conditions. No renewed speed guarantee is established by this code integration.

No staging, commit or push performed. Existing untracked report/presentation output preserved.

Final full-suite result: 243 tests executed in 131.599 seconds; 242 passed and one skipped. Existing Windows symlink skip retained. Deprecation and unclosed-event-loop resource warnings were emitted. JavaScript syntax checks and git diff --check passed. No real-model performance or live browser acceptance run was performed in this integration turn.
