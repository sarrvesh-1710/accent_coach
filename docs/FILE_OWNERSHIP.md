# File ownership and branch responsibilities

This is a coordination agreement, not GitHub-enforced access control. Existing teammate branches are preserved. Do not invent GitHub handles or enable required CODEOWNERS reviews before Lucas and Parthiban confirm their accounts.

| Owner | Feature branch | Primary area |
| --- | --- | --- |
| Sarrvesh Mahadevan | feature/speed-free-speech | audio_io.py, dsp_features.py, speech_content.py, assessment.py, analysis_service.py, lesson_catalog.py, phoneme_scoring/ analysis code; relevant tests and timing tools |
| Parthiban Nagesh | feature/voice-conversion | New voice_generation/ module, generation-specific tests, dependency file and playback component |
| Lucas Luna Giorgi | feature/profiles-personalization | New accounts/ and session_store/ modules, attempt_history.py integration, profile/history components and authorization tests |

## Shared files

- Sarrvesh coordinates app_2.py and pipeline.py integration. Teammates provide small components and reviewed wiring changes.
- site_server.py and site_pages.py: Lucas leads authentication/routing additions; coordinate with Sarrvesh before modifying existing practice routes.
- web_assets/site.css and practice.js: use feature-specific classes/components and coordinate shared selectors.
- prompts.json, phoneme_scoring/settings.json, requirements*.txt, site_config.json, README.md and contracts/: discuss changes first; they affect other subsystems.
- New generation dependencies belong in a separate file/environment if incompatible. No unannounced upgrades to shared Python/PyTorch/CUDA dependencies.

These ownership assignments describe the next sprint, not attribution for historical contributions. Anyone may propose a fix through review; ownership is not an exclusive editing permission.

## Integration workflow

Start all feature branches at the foundation commit. Open small PRs targeting team/week1-foundation. This branch is the integration branch; keep it runnable. Review and merge one PR at a time, then other owners merge origin/team/week1-foundation into their feature branches. Do not force-push teammates' branches. Do not merge the integration branch into main until the combined demo is tested and the team requests it.

Daily check-in: demonstrate progress, report interface/dependency changes and blockers, and confirm the next integration point. Shared changes require review by the affected owner; this rule is procedural until GitHub review settings are configured.
