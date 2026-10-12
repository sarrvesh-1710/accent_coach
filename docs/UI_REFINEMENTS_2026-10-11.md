# Requested interface refinements

## Implemented

- Reading pages use an 800-pixel maximum-width container with equal outer margins. This also applies to Terms for consistency.
- Steps 01 and 02 have matching white cards, 16-pixel corners, soft shadows, equal desktop widths, and equal desktop heights. They stack naturally on phones.
- All 12 configured sentences have a broad General American IPA guide. Target spellings are underlined, including “th” in “think.” These guides describe an example pronunciation, not measurements of the learner.
- A speaker-icon Listen button plays an optional local English example. Playback can be stopped; it resets at the end and when changing the sentence or starting a recording. Errors produce a visible message.
- The examples are explicitly labeled **synthetic**, generated with the installed Microsoft Zira Desktop en-US voice. They are not human native-speaker recordings. No reference audio is passed to scoring; `compare_reference=False` remains in the analysis call.
- Practice hint accordions now display downward chevrons when closed and upward chevrons when open.
- Check my recording uses `#0E4D40`, bold white text, and a darker hover state. It remains disabled, with reduced opacity, until a recording is ready.
- The existing microphone action is styled as a circular microphone button. Its real recording Stop control is red and pulses while active; paused recording does not pulse. Reduced-motion settings disable the animation. The browser's microphone permission and recording behavior are preserved.
- Processing text now says “Analyzing pronunciation…” and “Demo processing may take a few moments.” The three-minute upper limit remains visible so the UI does not promise an unrealistically short wait.
- How It Works now has four visual cards: Choose, Record, Analyze, and Feedback. Supported, Practice, and Inconclusive have green, amber, and neutral pill badges with text explanations.
- Stylesheet URLs now include a content hash. This fixes stale CSS appearing after an app update.

## Verification

- Full automated suite: **80 tests ran; 79 passed and one Windows symlink test was skipped**. Log: `runs/ui-refinements-tests.log`.
- All 12 playback files serve successfully, contain non-silent mono audio at 16 kHz, and have the expected prompt IDs. Their combined size is 771,752 bytes. Audit: `runs/listening-example-audit.json`.
- Browser playback entered Playing, then returned to Listen at the end. Changing to “The ship is here” updated the phrase, IPA, highlighted vowel, and audio URL.
- Desktop card widths were approximately 548 pixels each and heights matched exactly in the observed layout.
- How It Works and Privacy each measured 800 pixels wide on desktop with equal margins, within subpixel rounding.
- Practice, How It Works, and Privacy had no horizontal document overflow across tested narrow and wide layouts, including an actual 320-CSS-pixel layout. Audit: `runs/ui-refinements-responsive.json`.
- The black pill/dot was not reproduced in the rendered website header. No unrelated controls or application overlays were hidden to mask it.

## Remaining checks

The automated browser has no microphone, so live microphone capture and the active recording animation need a check on the user's microphone-enabled browser. Test Record, Stop, playback, and Check my recording once there. Native-speaker human examples can replace the synthetic listening files later if the team has permitted recordings; scoring must remain independent.

The earlier public-launch requirements are unchanged: custom domain and hosting, storage isolation for public users, policy review for that hosting, physical-device checks, and human validation of pronunciation feedback. These changes are local and have not been pushed or published.

## Main files

`app_2.py`, `site_pages.py`, `site_server.py`, `prompts.json`, `web_assets/site.css`, `web_assets/practice.js`, `web_assets/microphone.svg`, and `web_assets/examples/`.

`tools/build_practice_examples.ps1` regenerates the optional listening files on Windows with the installed voice. Their manifest records the voice, phrase, synthetic status, and exclusion from scoring.
