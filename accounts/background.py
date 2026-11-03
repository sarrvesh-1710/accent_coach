"""Optional background preferences and deliberately weak, reversible starter packs."""
import json
from pathlib import Path

COUNTRIES={row['code']:row['name'] for row in json.loads(Path(__file__).with_name('countries.json').read_text(encoding='utf-8-sig'))}
COUNTRIES['ZZ']='Other / multiple countries'
LANGUAGES={'':'Use country starter suggestion','spanish':'Spanish','japanese':'Japanese','mandarin':'Mandarin Chinese','english':'English','other':'Another language / multilingual'}
PACKS={
 'spanish':dict(order=['IH','AE','TH'],label='Spanish-language starter',source='https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2021.660917/full'),
 'japanese':dict(order=['AE','IH','TH'],label='Japanese-language starter',source='https://www.cambridge.org/core/journals/applied-psycholinguistics/article/abs/effects-of-identification-training-on-the-identification-and-production-of-american-english-vowels-by-native-speakers-of-japanese/69DD247F62AD56AF41AE3EBBE43FDAAC'),
 'mandarin':dict(order=['TH','IH','AE'],label='Mandarin-language starter',source='https://benjamins.com/catalog/jslp.20067.wie'),
}
COUNTRY_PACK={**{code:'spanish' for code in ('ES','MX','AR','CO','PE','CL','EC','GT','CU','BO','DO','HN','PY','SV','NI','CR','PA','UY','VE')},'JP':'japanese','CN':'mandarin','TW':'mandarin'}
DEFAULT=dict(country='',language='',use_starters=True)


def validate_background(value):
    if not isinstance(value,dict):raise ValueError('Choose valid background preferences.')
    country=value.get('country','');language=value.get('language','');enabled=value.get('use_starters',True)
    if not isinstance(country,str) or (country and country not in COUNTRIES):raise ValueError('Choose an available country or skip this question.')
    if not isinstance(language,str) or language not in LANGUAGES:raise ValueError('Choose an available language background.')
    if type(enabled) is not bool:raise ValueError('Choose whether to use starter suggestions.')
    return dict(country=country,language=language,use_starters=enabled)


def starter_plan(background):
    language=background['language'] or COUNTRY_PACK.get(background['country'],'')
    pack=PACKS.get(language) if background['use_starters'] else None
    return dict(order=pack['order'] if pack else ['TH','IH','AE'],label=pack['label'] if pack else 'Balanced starter check',
        source=pack['source'] if pack else None,tailored=bool(pack),country_label=COUNTRIES.get(background['country'],''),
        explanation='Starter suggestions are optional practice ideas, not predictions about your ability. Your goals and personal results take priority. All lessons remain available.')
