# Profile pivot — October 27, 2026

Active local branch: `parth/profile-improvements`, based on the integrated team
site at `e7f57d9`. No teammate branch was changed or deleted. This branch is prepared for publication and team review.

## Preserved work

The unfinished Kokoro merge and connection are preserved on
`backup/kokoro-integration-2026-10-27` at `17660e3b7d791c66e5e587fe4136388120efc2a6`.
A verified complete recovery bundle and local-settings copy are under ignored
`runs/profile-pivot-backup-2026-10-27/`. The in-progress merge was aborted after
that backup. `feature/voice-conversion` remains at its committed `09f6de1` state.

Account data, recordings, models, generation environments and local speech settings
remain in place. A local Git exclusion protects `private_data/` even on older
branches that did not yet include that directory in their shared ignore rules.
The unfinished Kokoro connection is parked; this profile branch starts from the
integrated team's Windows synthetic-example backend.

## Initial profile work

- Clear TH / think, IH / ship and AE / bad sound preferences.
- Visible unsaved-change state, save and discard controls, and saving feedback.
- Display name updates in the profile heading and sign-in label after saving.
- Server-canonical saved values are returned to the form; whitespace is trimmed
  and duplicate goals removed using the existing validation/storage behavior.
- Validation errors preserve saved values; network failure preserves draft edits.
- Existing account ownership, CSRF protection, password handling and database
  fields are retained. No profile schema migration was introduced.

Changes are limited to the profile route/save response, its dedicated browser
assets, removal of the old duplicate save handler, and profile tests. Review shared
account/UI changes with Lucas before team integration.

## Verification

The full profile-branch suite ran 160 tests: 159 passed, with one existing Windows
symlink skip. Five focused profile checks cover canonical save/persistence,
general-practice preferences, invalid input, account isolation/CSRF, and escaped
display names. Browser checks with a disposable test account verified dirty state,
discard, saving, immediate name updates, and persistence after reload. Your real
account was not used for these tests.

## Run

From the main `accent_coach` repo:

```powershell
.\.venv\Scripts\python.exe app_2.py
```

Open http://127.0.0.1:7861/profile and sign in using your existing local account.
Merge `parth/profile-improvements` for the profile changes. The separate
`backup/kokoro-integration-2026-10-27` branch preserves the parked Kokoro work;
it is not part of this profile change and should be reviewed separately.
