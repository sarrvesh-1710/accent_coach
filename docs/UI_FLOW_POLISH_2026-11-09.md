# UI flow and responsive polish

Implemented the attached 89-point review without changing speech models or assessment settings.

Sentence uses a dedicated responsive 32-40px style and semantic speaking section grouping sentence, focus, example and capture. Sidebar uses 15-17rem bounds with a 56rem stacking breakpoint. Mobile receives a compact progress summary from the same existing plan response; detailed plan stays below recording. No extra polling or model work.

Latest-sound cards use a column layout with bottom-aligned real navigation links, and recording dates remain subdued. Shared 8/12/16/24/32px spacing tokens, native checkbox labels, focus outlines and disabled controls retained. Contrast calculations: ink/white 14.19:1; supporting text/soft panel 6.61:1; teal/white 5.32:1; white/primary 9.75:1; white/stop 7.64:1. These evaluate the named color pairs, not a complete accessibility audit.

Practice presentation states explicitly cover idle, requesting permission, recording, preparing playback, preview, analyzing, result and error. Existing asynchronous epoch/revision mechanisms remain. Repeated save clicks are guarded. Recording timer and level updates are silent; state transitions are announced by the polite status region. Stop is prominent during capture, and preview controls are guarded while busy. These do not bypass transcript confirmation in custom/free speech.

Browser checks used isolated route-generated HTML with sample responses and temporary accounts, without microphone or real inference. Verified 390, 768, 896, 900 and 1140px frames. No horizontal overflow or multiline step status; computed sentence sizes 32px narrow, 36px at 900, 40px wide. Mobile summary visible at narrower widths and absent on wide desktop. This is browser layout evidence, not live backend acceptance or a physical phone test.

Controlled tests: account renderer 35 scenarios includes preview/submission/duplicate guard, existing stale-result/results/retry coverage; profile rendering and microphone lifecycle wrappers, seven account integration tests passed. Full run results in output/ui-flow-regression-20261109.log. Preview server stopped after checks. Existing warning messages remain visible in logs.

No commit or push. Real microphone permission, spoken recording-to-feedback acceptance and comparable speed retest remain the next work. No measured latency improvement or guarantee is claimed.

Final full regression: 245 tests in 107.396 seconds; 244 passed, one Windows-specific skip. Deprecation and asyncio resource warnings were emitted. No test failures.
