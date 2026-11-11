# UI hierarchy refinement

Updated sentence sizing and spacing, removed non-clickable target underline, standardized 18px select chevrons, reduced guide/recommendation container borders, strengthened selected sound tiles, grouped History into date containers, and added example words to short sound labels. Starting check title is shorter with a sentence-count subtitle.

Information-page account menus use the existing authenticated identity and CSRF sign-out. Anonymous pages remain public without account identity. Existing no-store middleware remains effective. Tests use temporary accounts and stores.

Verified 34 controlled renderer cases (including grouped History, transcript/loading/saved/inconclusive states and evidence-based recommendations), 11 controlled microphone lifecycle cases (including timer, permission denial and cleanup), profile renderer, seven account integration tests, and information-page header login/logout regression. An initial header test expected an exact Cache-Control string; it was corrected to recognize the existing stronger no-store middleware response.

No actual browser screenshots, phone acceptance, fresh microphone recording or speed benchmark performed. Speech analysis and generation paths unchanged. Existing local work preserved; no commit or push.


Additional 88-point review refinement: sentence now 30-36px, repeated starting-check subtitle/current-index removed, explicit scope distinguishes new check recordings from earlier saved observations, profile guidance moved into details, profile gaps tightened, next recommendation uses horizontal desktop composition, and recording elapsed time has its own visible output. Start new practice is the prominent result action. Controlled renderer/profile/account/preference checks passed; no physical/browser speed claims added.
