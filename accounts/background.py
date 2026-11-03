"""Optional background preferences and deliberately weak, reversible starter packs."""
LANGUAGES={'':'Skip / balanced starter','arabic':'Arabic','hindi':'Hindi','japanese':'Japanese','mandarin':'Mandarin Chinese','spanish':'Spanish','other':'Another language / multilingual'}
PACKS={
 'hindi':dict(order=['TH','AE','IH'],label='Hindi-language starter',source='https://iu.pressbooks.pub/hindiscript/chapter/5-1-discussion/'),
 'arabic':dict(order=['IH','AE','TH'],label='Arabic-language starter',source='https://discovery.ucl.ac.uk/10044993/'),
 'spanish':dict(order=['IH','AE','TH'],label='Spanish-language starter',source='https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2021.660917/full'),
 'japanese':dict(order=['AE','IH','TH'],label='Japanese-language starter',source='https://www.cambridge.org/core/journals/applied-psycholinguistics/article/abs/effects-of-identification-training-on-the-identification-and-production-of-american-english-vowels-by-native-speakers-of-japanese/69DD247F62AD56AF41AE3EBBE43FDAAC'),
 'mandarin':dict(order=['TH','IH','AE'],label='Mandarin-language starter',source='https://benjamins.com/catalog/jslp.20067.wie'),
}
DEFAULT=dict(language='',use_starters=True)


def validate_background(value):
    if not isinstance(value,dict):raise ValueError('Choose valid background preferences.')
    language=value.get('language','');enabled=value.get('use_starters',True)
    if language=='english':language='other'  # Earlier clients used an English/balanced option.
    if not isinstance(language,str) or language not in LANGUAGES:raise ValueError('Choose an available language background.')
    if type(enabled) is not bool:raise ValueError('Choose whether to use starter suggestions.')
    return dict(language=language,use_starters=enabled)


def starter_plan(background):
    language=background['language']
    pack=PACKS.get(language) if background['use_starters'] else None
    return dict(order=pack['order'] if pack else ['TH','IH','AE'],label=pack['label'] if pack else 'Balanced starter check',
        source=pack['source'] if pack else None,tailored=bool(pack),
        explanation='Starter suggestions are optional practice ideas, not predictions about your ability. Your goals and personal results take priority. All lessons remain available.')
