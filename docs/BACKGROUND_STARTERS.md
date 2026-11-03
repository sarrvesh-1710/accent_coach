# Optional background starter design

Country of origin is an optional user-entered context, not a diagnosis, language
identifier, ethnicity classifier or scoring input. Countries contain many language
communities; the optional language selector always overrides the country shortcut.
Names come from a static snapshot of 244 Windows/.NET region names, plus an
Other / multiple countries choice. No runtime country lookup or new package is
required. Blank/omitted fields remain valid.

## Current starter catalog

These are editorial lesson-order choices grounded in language research, not a
validated ranking of the most common errors by country. The three existing target
sounds remain available to everyone and no measurements are manufactured.

- Spanish background: IH, AE, TH. Spanish-language study motivates exploring the
  English /i/-/I/ contrast; the other sounds remain introductory checks.
- Japanese background: AE, IH, TH. Japanese learner research motivates exploring
  the /ae/ vowel. Remaining sounds are introductory checks.
- Mandarin background: TH, IH, AE. Mandarin learner fricative research motivates
  exploring TH. Remaining sounds are introductory checks.
- Other languages/countries, English, skipped questions and opt-out: balanced
  TH, IH, AE. Unsupported country packs are not invented.

The country-to-pack shortcuts in `accounts/background.py` are tentative language
suggestions for countries associated with those language backgrounds, not evidence
that an individual speaks that language. An explicit language or multilingual
choice overrides the shortcut. These defaults need user evaluation before claims
about educational effectiveness.

## Adaptation and user control

Personal results are computed from the signed-in owner's current saved analyses.
When any current sound observation exists, all background tie-breaks are disabled.
Within the existing feedback priority (possible substitution, uncertain, untested,
expected-supported), selected sound goals take priority; background is used only
to break remaining ties for a new learner. No lesson is locked or filtered out.
Removing/deleting all current feedback permits a starter plan again. Historical
invalidated or deleted results are not retained as hidden demographic evidence.

Country and language persist separately in an additive `learning_preferences`
table. The existing users table and password hashes are untouched. Invalid input
rejects the whole profile update. Existing clients omitting the new background
field retain their previous values. Only authenticated owner-scoped profile routes
read or modify these preferences, with the existing CSRF checks for writes.

## Primary references

- ASHA, Accent Modification: first-language influence and individualized assessment:
  https://www.asha.org/practice-portal/professional-issues/accent-modification/
- When the Easy Becomes Difficult: Factors Affecting the Acquisition
  of the English /i:/-/I/ Contrast (2021):
  https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2021.660917/full
- Lambacher et al., identification/production training of American English vowels
  by native Japanese speakers (2005):
  https://www.cambridge.org/core/journals/applied-psycholinguistics/article/abs/effects-of-identification-training-on-the-identification-and-production-of-american-english-vowels-by-native-speakers-of-japanese/69DD247F62AD56AF41AE3EBBE43FDAAC
- Acquisition of non-sibilant anterior English fricatives by adult second language
  learners (2021), Mandarin-English speakers:
  https://benjamins.com/catalog/jslp.20067.wie

These studies concern language groups and particular tasks. They do not validate
country-based individual error predictions, this app's starter ordering, or the
app's pronunciation feedback accuracy.
