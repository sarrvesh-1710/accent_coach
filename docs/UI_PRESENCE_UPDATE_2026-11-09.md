# UI presence revision

Implemented the next review recommendations on the existing local UI.

- Consistent system sans-serif type, 16px body, 14px supporting text, 32-36px titles and larger navigation.
- Practice sentence uses 28-32px text and configured target-word highlighting. Focus labels come from lesson metadata; they are lesson goals, not assessment outcomes. No injected HTML is used for sentence text.
- Practice next uses saved suggestion evidence and a matching configured lesson. With no evidence, it invites a starting check without inventing a sound finding.
- Profile uses account/preferences left and plan right, with progress below. Columns stack on smaller screens.
- History rows have Review attempt actions and status badges. Original playback remains inside the reviewed attempt, without loading every recording into the list.
- Starting checks render one numbered segment per configured step, with current/complete states taken from saved plan data. Practice completion does not imply mastery.
- Signed-in identity and CSRF-protected sign-out moved into an accessible native details menu in the site header. Reduced practice/footer spacing and consistent controls.

Validation: 33 controlled account-rendering cases passed, including target highlighting, free-speech focus hiding, saved-evidence recommendations, History filters, playback and stale-result presentation. Dedicated profile-rendering wrapper passed, account integration 7 passed, profile preferences 7 passed and lesson-plan integration 13 passed. Syntax and git diff --check passed. A test fixture variable-shadowing issue was corrected before the final rendering run.

No real microphone, browser screenshots, responsiveness observation or new performance measurement was executed in this revision. Models, analysis settings and optional generation code remain untouched. Live visual acceptance is still needed. No commit/push.
