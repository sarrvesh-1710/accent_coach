# Profile and speed integration — November 4, 2026

Current feature branch: profile-system. Main is untouched at 913288392570092d4ecdfb3bd3053756a92f30c8.

Imported Sarvesh’s speed-only commit 7c39524b642cec26b4e279d5b96aa017a718547c as 0ac5ab2, retaining his authorship and cherry-pick attribution. It adds owned MFA interpreter reuse, dictionary-resource caching, optional lexicon graph reuse, and regression tests. The later cdf1e56 UI/profile integration and 529e28e documentation publication were not imported; they also contain unrelated replacements overlapping this branch’s newer recording and profile screens. This is a targeted speed integration, not a complete merge of feature/speed-free-speech.

The imported fast path explicitly supports direct Windows MFA 3.3.7. This laptop currently has a module-based MFA 3.4.2 installation. Existing local settings remain unchanged; unsupported runtimes keep ordinary CLI alignment. Do not claim the optimized path is active or that latency improved on this laptop. A separate supported-runtime setup and measurement are needed before claiming speed gains. Do not remove Sarvesh’s version safeguards merely to enable reuse.

Cleanup review found these local and origin branches already fully included in profile-system:

- parth/application-feedback at b4d6ebeb613e610b6e95ba32810b03a2c43c0543.
- parth/profile-improvements at fac721979d86643f73bdc65e6627264ea71495ea.

Both were checked for ancestry and matching local/remote tips; neither is checked out in an active worktree. Deletion is pending the user’s explicit confirmation. No branch deletion was performed. Other teammates’ branches and backup branches are retained.

Validation: the combined Python suite ran 234 tests (233 passed, one Windows symlink skip), including the imported worker/cache tests. Twenty client logic checks passed. The real speech/Kokoro integration rehearsal passed all 50 checks using public synthetic fixtures and temporary accounts. That run measured 35.27 seconds for analysis, 30.53 seconds for cold generation, and 0.58 seconds for warm generation; those figures validate this rehearsal only, not speed gains or human pronunciation accuracy. The imported speed implementation files match the source branch. The sample starting-check screen was also verified in the browser without accessing the physical microphone.
