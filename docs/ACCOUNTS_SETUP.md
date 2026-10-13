# Working local accounts, profiles, and saved practice

This implementation supersedes the earlier unconnected Day 1 patch. It is built against branch `feature/profiles-personalization` at `8c4fa455621079da003134eb67b8d23080e00475`.

## Start on your existing Windows installation

Activate the same environment that already runs Accent Coach and work from the repository folder:

```powershell
python -m pip install -r requirements-accounts.txt
python site_server.py
```

`python app_2.py` also starts the new account website. Open `http://127.0.0.1:7861/`. Stop the old app before restarting. Your existing MFA environment, downloaded models, and `phoneme_scoring/settings.local.json` still apply.

1. Choose **Create an account**, enter a username, display name, and a password of at least 12 characters.
2. Open **My profile**, choose preferred practice sounds, and save.
3. In **Practice**, choose a sentence, record with the microphone or upload a WAV, then choose **Check and save my recording**.
4. The recording is saved to your account before analysis starts. The result is saved when analysis finishes. Processing failure leaves the recording and failure status in history.
5. Open **My history** to replay, download results, or delete an attempt. History remains after sign-out, app restart, and another user signing in.

The speech pipeline is the existing preset pipeline. Custom-text/free-speech assessment and generated-example jobs remain the other teammates' integration work; this change does not invent those features or validated pronunciation scores.

## Storage and privacy

Local accounts use Argon2 password hashes, opaque revocable login cookies, CSRF checks, and SQLite transactions. Profile, history, recording playback, result downloads and deletion all use the verified login session to select the owner. There is no browser-supplied owner parameter. There is no external identity provider, API key or email verification requirement.

The app stores accounts, recording blobs and results in ignored `private_data/accounts.sqlite3`, with temporary private analysis folders under `private_data/work/`. Set `ACCENT_COACH_DATA_DIR` to an absolute directory to relocate it. Keep the complete data directory if moving installations; stop the app before copying it. The database is local and not encrypted against someone with operating-system access.

The server remains bound to localhost. Run one server per data directory. Account recovery/email delivery, public deployment, account deletion and automatic retention are outside this local milestone. Seven-day login sessions can be revoked by signing out. Attempt deletion removes its recording/result fields and prevents late completion from restoring them; backups/downloads are separate copies.

Old unowned `runs/` files are left intact and are not assigned to whichever account signs up first. The legacy `app.py` and old history helper are not used by the new website. The private website does not mount Gradio's file server; all saved learner audio uses authenticated routes.

## Integration changes

- `accounts/store.py`: persistent accounts, profiles, login sessions and private attempts.
- `accounts/web.py`: working sign-up/sign-in, profile, practice and history pages, authenticated APIs, bounded job queue.
- `web_assets/accounts.js` / `.css`: browser UI, microphone WAV conversion, upload, polling, playback, profile saving and deletion.
- `site_server.py`: mounts the account website and existing public/static pages.
- `pipeline.py` / `analysis_service.py`: optional server-controlled `output_root` keeps new account jobs out of shared `runs/`; existing callers retain their default behavior.
- `app_2.py`: existing launch command starts the account site.

Attempts are immutable recordings: editing/replacing a recording starts a new attempt. A tombstoned attempt cannot be completed by a late worker. A restart marks interrupted jobs as failed while retaining the recording. A worker never takes output paths from browser input.

## Verification

```powershell
python -m unittest discover -s tests -v
```

The full suite passed 86 tests in the implementation environment. New HTTP tests cover the complete registration/profile/upload/result/history/logout/login path, two-user access denial (including playback/download/delete), restart persistence, CSRF, bad audio, deletion during processing and analysis failure. Speech-worker substitution in those tests checks wiring; it does not measure model accuracy.

A browser check also exercises the real server and pipeline; the final verification report records its result and the model-availability limitation of this environment.

### Executed browser result

Headless Chromium exercised account creation, WAV upload, simulated microphone capture and conversion, the actual worker/pipeline call, saving a profile, reopening history, signing out/back in, and a 390-pixel mobile viewport. It completed without JavaScript errors. The real pipeline returned partial/inconclusive feedback because Whisper/MFA/model assets are not installed in this test environment; recording and result persistence worked. This is not a human-pronunciation accuracy test. Physical microphone permission/device behavior should still be checked on the demo laptop.
