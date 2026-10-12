# Accent Coach frontend update

Date: October 11, 2026  
Team: Accent coach #3  
Contact: sarrveshm@tamu.edu

## Outcome

The local website now has a restrained, responsive interface with a clear three-step flow: choose a sentence, record your voice, and review the result. Run `app_2.py` and open <http://127.0.0.1:7861/>. The frontend update preserves the reference-free pronunciation pipeline and its experimental assessment limits.

These changes are in the local working copy. They have not been published or pushed to GitHub as part of this frontend update. The existing working-copy changes have been preserved.

## Changes delivered

| Request | Implementation |
| --- | --- |
| Clear visual design | Warm white background, dark text, teal accents, system fonts, rectangular buttons, and direct instructions. No purple gradients, pill buttons, emoji icons, stock photographs, invented metrics, testimonials, counters, or decorative animations were added. Authored interface copy uses no em dashes. |
| Understandable practice flow | One primary recording action; recognized words, a short experimental result, replay, and a next step. Practice hints and technical diagnostics stay in expandable sections. |
| Mobile layout and horizontal scrolling | Columns stack on narrow screens. Long text wraps. Technical tables are replaced by responsive cards, with precise underlying values retained in the results download. |
| Mobile navigation and clickable logo | A working Menu control on narrow screens. The logo returns to the practice page. Navigation contains only implemented pages. |
| Favicon and lightweight assets | Custom waveform SVG logo (217 bytes) and ICO favicon (1,526 bytes). No large photographic assets or downloaded fonts. Gzip compression is enabled for suitable responses, including the stylesheet. |
| Titles and descriptions | Individual page titles and meta descriptions for Practice, Help, Privacy, Terms, and the missing-page screen. The local prototype requests no search indexing. |
| Footer and contact details | Dynamic copyright year, the supplied team name, working internal links, and a clickable `mailto:sarrveshm@tamu.edu` link. No phone is displayed, as requested. |
| Policy pages | `/privacy` describes the current local audio, result, browser history, and cache behavior. `/terms` explains prototype use and the limits of experimental feedback. These must be checked against the eventual hosting arrangements before public release. |
| Custom 404 | Missing page addresses return a branded page with a return-to-practice link and an actual HTTP 404 status. API errors remain machine-readable. |
| Success and error messages | Recording-ready, processing, saved-result, retry, history refresh, missing-attempt, and deletion-confirmation messages. Existing analysis failure handling remains available. |
| Optional builder branding | Optional Gradio footer links are disabled. No fabricated reviews, “made with AI” label, placeholder contact details, or unused navigation are present in the authored site. |

## What the app does now

- Offers 12 configured short English practice sentences.
- Accepts microphone input or uploaded audio, with a 10 MB upload limit and a five-second recording limit.
- Uses the existing Whisper content check, MFA alignment, and phoneme-model evidence without requiring a reference recording.
- Reports experimental evidence for configured practice sounds, with an actionable practice hint when appropriate.
- Supports replay, another attempt, saved-attempt review, explicitly confirmed deletion, and a downloadable analysis file.
- Keeps processing details accessible to the team without placing them in the main learner flow.

This remains a local prototype. It does not provide a validated pronunciation percentage, pass/fail grade, arbitrary-sentence assessment, or authenticated public accounts.

## Verification

1. **Automated suite:** 78 tests ran, 77 passed, and one Windows symlink test was skipped because symlink creation was unavailable. Evidence: `runs/frontend-tests-final.log`.
2. **Responsive pages:** Practice, Help, Privacy, Terms, and the custom 404 were checked with browser viewport settings of 320, 390, 768, and 1280 pixels. All 20 checks showed page content fitting the available document width. Evidence: `runs/responsive-audit.json`.
3. **Routes and metadata:** Internal links, page titles, descriptions, favicon, HTTP 404 behavior, JSON API error behavior, and stylesheet compression passed automated checks.
4. **Full browser attempt:** A synthetic “I think so” WAV was uploaded through the redesigned page. The app displayed the recognized sentence, experimental target-sound feedback, playback controls, and a saved-result message. The saved result records `reference_comparison_requested: false`. This verifies integration, not accuracy on human speech. Evidence: `runs/20261011T192734_de3bc631b5fc/results.json`.
5. **Saved-attempt controls:** Refresh displayed a success message. An unconfirmed delete displayed its confirmation instruction and did not delete a recording.
6. **Result layout and retry:** Populated sound evidence and processing-stage cards fit a narrow browser view. Record again cleared the current recording and result and displayed instructions for another try.
7. **Silence error:** A silent WAV produced “We could not hear your voice,” explained that the recording was silent or too quiet, and offered Record again.
8. **External lesson links:** Automated HTTP requests received 403 responses, but a separate web retrieval confirmed all three existing Rachel's English lesson pages. A blocked automated request is not evidence of a missing page. The external URLs were retained. Evidence: `runs/site-link-audit.json`.

The external lesson pages checked were [TH consonants](https://rachelsenglish.com/english-pronounce-th-consonants/), [IH vowel](https://rachelsenglish.com/english-pronounce-ih-vowel/), and [AA/AE vowel](https://rachelsenglish.com/english-pronounce-aa-ae-vowel/). Their availability is controlled by the external site.

## What remains before public launch

1. Choose hosting and a custom domain, connect DNS, and verify HTTPS. No domain was supplied, so none has been invented or connected.
2. Add authentication and user-isolated recording storage before offering the app to multiple people online. The current saved-attempt list belongs to this laptop.
3. Review Privacy and Terms against the actual host, audience, data retention, and operator arrangements. The current wording describes the local prototype and is not a claim of legal compliance.
4. Test a real microphone, permissions, replay, and deletion on actual target phones and browsers. Browser viewport checks do not substitute for physical Android/iPhone testing. The automated browser had no microphone available; uploaded synthetic audio was used.
5. Complete the separate human pronunciation validation plan. A polished interface does not establish model accuracy.

`tools/check_site_readiness.py` reports these remaining items and deliberately does not mark the site ready for public launch. The server remains bound to `127.0.0.1`.

## Files to know

- `app_2.py`: learner interface and existing analysis callbacks.
- `site_pages.py`: shared header/footer, metadata, policy pages, Help, and responsive result cards.
- `site_server.py`: local server, routes, custom 404, compression, and port handling.
- `site_config.json`: supplied team/contact details; phone and public URL are unset.
- `web_assets/`: stylesheet, SVG logo, and favicon.
- `tests/test_site.py`: website regression checks.
- `tools/check_site_readiness.py`: remaining launch requirements.

## Quick review on this laptop

1. Open <http://127.0.0.1:7861/>. If the server is stopped, run `.\.venv\Scripts\python.exe app_2.py` from the repository folder.
2. Choose a sentence, record or upload it, and press **Check my recording**. Confirm the result, replay, and saved message appear.
3. Press **Record again**. Confirm the old recording/result clear before a new attempt.
4. Open **Saved attempts**, refresh the list, and select an earlier result. Use deletion only for an attempt you intend to remove.
5. Open Help, Privacy, and Terms. Try `/missing-page` to see the custom 404.
6. On a narrow screen, open Menu and confirm every page fits without sideways scrolling.

## Screenshots

Desktop and narrow-screen screenshots are saved beside the repository in `../work/frontend-desktop.jpg` and `../work/frontend-mobile.jpg`. The screenshots show the automated browser without a microphone; actual microphone testing remains a device rehearsal step.
