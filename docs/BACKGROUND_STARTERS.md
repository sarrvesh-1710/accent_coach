# Optional language starter design

The user can choose Arabic, Hindi, Japanese, Mandarin Chinese or Spanish at
signup or in My profile. Skip, another language / multilingual and opt-out all
produce a balanced TH/IH/AE starter. Country is not collected or inferred.

## Initial starter catalog

The order is an editorial choice for introductory listening/recording exercises,
not a validated ranking of errors or a prediction about an individual.

- Arabic: IH, AE, TH. Begin by exploring English vowel contrasts.
- Hindi: TH, AE, IH. Explore the fricative in think versus a stopped consonant.
- Japanese: AE, IH, TH. Explore the vowel in bad.
- Mandarin Chinese: TH, IH, AE. Explore the dental fricative in think.
- Spanish: IH, AE, TH. Explore the vowel contrast in ship/sheep.

Only the three existing sound contrasts are assessed. These profiles do not add
new phoneme models or grading capabilities. Dialects, experience and multilingual
backgrounds vary; every sound and lesson remains available to every user.

## Adaptation and user control

The signed-in owner's current saved results determine personal coaching. Once any
current sound observation exists, language-based tie-breaks are disabled. Within
the feedback priority (possible substitution, uncertain, untested,
expected-supported), selected goals take priority over starter ordering.
Deleting or invalidating all current feedback allows a starter plan again;
removed results are never retained as hidden evidence. Preferences are optional,
editable and removable, with visible save/discard controls.

An additive learning_preferences table retains its old country column for schema
compatibility. The app never reads it for profiles or recommendations, writes an
empty string on preference saves, and never infers a language from it. Explicit
saved language choices survive this change; the earlier English/balanced choice
maps to another language / multilingual. Existing clients can omit background to
preserve saved preferences. Authenticated ownership, CSRF and atomic validation
remain in place. The profile API exposes only language and use_starters for the
background. The obsolete country-name dataset has been removed.

## Primary research and teaching references

These motivate topics to explore, not demographic error probabilities or this
app's efficacy. Some studies use British English; they do not validate this app's
General American feedback or the complete starter ordering.

- General language influence and individualized assessment:
  https://www.asha.org/practice-portal/professional-issues/accent-modification/
- Spanish, English /i:/-/I/ acquisition:
  https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2021.660917/full
- Japanese, American English vowel training:
  https://www.cambridge.org/core/journals/applied-psycholinguistics/article/abs/effects-of-identification-training-on-the-identification-and-production-of-american-english-vowels-by-native-speakers-of-japanese/69DD247F62AD56AF41AE3EBBE43FDAAC
- Mandarin-English fricative acquisition:
  https://benjamins.com/catalog/jslp.20067.wie
- Arabic learners, English vowel/consonant perception and production:
  https://discovery.ucl.ac.uk/10044993/
- Hindi dental stops and the English th sounds, Indiana University teaching text:
  https://iu.pressbooks.pub/hindiscript/chapter/5-1-discussion/
