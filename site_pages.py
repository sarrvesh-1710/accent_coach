"""Shared site shell, accurate local-prototype notices, and page metadata."""
from datetime import date
import html
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'web_assets'
PRACTICE_TITLE = 'English pronunciation practice | Accent Coach'
PRACTICE_DESCRIPTION = 'Record a short English sentence, check a practice sound, and listen to your saved attempts. Experimental feedback without reference audio.'


def stylesheet_html():
    revision = hashlib.sha256((ASSETS / 'site.css').read_bytes()).hexdigest()[:12]
    return f'<link rel="stylesheet" href="/site-assets/site.css?v={revision}">'


def load_site_config():
    config = json.loads((ROOT / 'site_config.json').read_text(encoding='utf-8'))
    if not config.get('owner') or not config.get('brand'):
        raise ValueError('Site brand and owner are required.')
    if config.get('email') and not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', config['email']):
        raise ValueError('Site contact email is invalid.')
    if config.get('phone') and not re.fullmatch(r'\+?[0-9 ()-]{7,24}', config['phone']):
        raise ValueError('Site phone number is invalid.')
    if config.get('public_url'):
        parsed = urlparse(config['public_url'])
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.query or parsed.fragment or parsed.path not in {'', '/'}:
            raise ValueError('Public URL must be a complete HTTPS site origin.')
    return config


def contact_links(config):
    links = []
    if config.get('email'):
        email = html.escape(config['email'], quote=True)
        links.append(f'<a href="mailto:{email}">{email}</a>')
    if config.get('phone'):
        phone = html.escape(config['phone'])
        dial = re.sub(r'[^+0-9]', '', config['phone'])
        links.append(f'<a href="tel:{dial}">{phone}</a>')
    return ''.join(links)


def header_html(current='/'):
    config = load_site_config()
    links = ''.join(f'<a href="{url}"' + (' aria-current="page"' if current == url else '') + f'>{label}</a>'
                    for url, label in [('/', 'Practice'), ('/help', 'How it works'), ('/privacy', 'Privacy')])
    return ('<a class="skip-link" href="#main-content">Skip to content</a><header class="site-header">'
            f'<a class="site-brand" href="/" aria-label="{html.escape(config["brand"])} home">'
            '<img src="/site-assets/favicon.svg" alt="" width="36" height="36">'
            f'{html.escape(config["brand"])}</a><nav class="desktop-nav" aria-label="Main navigation">{links}</nav>'
            '<details class="mobile-nav"><summary aria-label="Open navigation menu">'
            '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M2 5h16M2 10h16M2 15h16"/></svg>'
            f'Menu</summary><nav class="mobile-links" aria-label="Mobile navigation">{links}<a href="/terms">Terms</a></nav></details></header>')


def footer_html():
    config = load_site_config()
    return ('<footer class="site-footer"><p>'
            f'© {date.today().year} {html.escape(config["owner"])}.<br>English pronunciation practice.</p>'
            '<nav class="footer-links" aria-label="Footer navigation"><a href="/help">Help</a>'
            '<a href="/privacy">Privacy policy</a><a href="/terms">Terms &amp; Conditions</a>'
            f'{contact_links(config)}</nav></footer>')


def meta_html(description, path='/', *, not_found=False):
    config = load_site_config()
    canonical = (f'<link rel="canonical" href="{html.escape(config["public_url"].rstrip("/") + path, quote=True)}">'
                 if config.get('public_url') and not not_found else '')
    return (f'<meta name="description" content="{html.escape(description, quote=True)}">'
            '<meta name="theme-color" content="#11675b"><meta name="robots" content="noindex, nofollow">'
            '<link rel="icon" type="image/svg+xml" href="/site-assets/favicon.svg">' + canonical)


def page_html(title, description, body, path, *, not_found=False):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{html.escape(title)} | Accent Coach</title>' + meta_html(description, path, not_found=not_found)
            + stylesheet_html() + '</head><body><div class="site-shell">'
            + header_html(path) + '<main id="main-content" class="document" tabindex="-1">'
            + body + '</main>' + footer_html() + '</div></body></html>')


def privacy_page():
    config = load_site_config()
    owner = html.escape(config['owner'])
    contact = contact_links(config)
    body = f'''<p class="eyebrow">Your recordings</p><h1>Privacy policy</h1>
    <p class="intro">This notice covers the local Accent Coach prototype operated by {owner}.</p>
    <p><small>Updated October 11, 2026</small></p>
    <h2>What the app stores</h2><p>When you record or upload audio, the app processes your voice, the selected sentence, recognized words, sound measurements, analysis results, and processing messages. Completed attempts receive a timestamp and an identifier. Audio and results are saved on the computer running the app. In this local version, that is the demo computer.</p>
    <h2>How recordings are used</h2><p>The app uses recordings to check the selected sentence and produce experimental feedback about a practice sound. It does not use your attempts to train its models or identify who you are. Speech models run locally using previously downloaded files. No reference recording is needed.</p>
    <h2>Who can access them</h2><p>This is a single-user local application. People with access to the demo computer or its saved files may be able to hear recordings and read results. Saved history is not separated into private user accounts. Record only with the speaker's permission and avoid including sensitive information.</p>
    <h2>Storage and deletion</h2><p>Saved attempts stay on the demo computer until deleted. Open <strong>Saved attempts</strong>, choose a completed attempt, select the deletion confirmation, and press <strong>Delete selected attempt</strong>. This removes that attempt's saved folder and audio.</p><p>Temporary upload and playback copies may remain in the app's cache. Cache cleanup runs hourly and expires copies older than 24 hours while the app is running. Your browser may retain playback copies, preferences, or framework run history. Deleting an attempt does not immediately remove browser copies, downloaded files, or backups. Close old pages and clear browser data if needed. Incomplete attempts are not listed in history; contact the team for help removing them.</p>
    <h2>External services and links</h2><p>Gradio analytics are disabled for this app. The site uses local assets and system fonts. Initial model setup downloads files from model providers. Optional pronunciation lessons open third-party websites, which have their own privacy practices. Recordings are not sent to those lesson sites by this app.</p>
    <h2>Questions or deletion help</h2><p>Contact {owner}: {contact}</p>
    <p class="document-note">This notice describes the local prototype. A hosted service would have different access and storage arrangements, which must be reviewed and described before public launch.</p>'''
    return page_html('Privacy policy', 'How Accent Coach stores, uses, and deletes recordings in the local prototype.', body, '/privacy')


def terms_page():
    config = load_site_config()
    body = f'''<p class="eyebrow">Using the prototype</p><h1>Terms &amp; Conditions</h1>
    <p class="intro">Accent Coach is an English pronunciation practice prototype from {html.escape(config['owner'])}.</p>
    <p><small>Updated October 11, 2026</small></p>
    <h2>Purpose and limitations</h2><p>The app offers experimental feedback on selected English sound contrasts. Recognition, alignment, and sound comparisons may be incorrect or unavailable. Results are not validated pronunciation grades, language certifications, or a measure of a person's ability. Use them as practice guidance.</p>
    <h2>Your recordings</h2><p>Submit only recordings you have permission to use. Obtain the speaker's permission before recording or uploading their voice. Do not upload private information about another person without their permission. You retain ownership of your recordings. The app processes and stores submitted audio to provide its practice features as described in the <a href="/privacy">privacy policy</a>.</p>
    <h2>Appropriate use</h2><p>Use the app for pronunciation practice and evaluation of the prototype. Do not use it to harass speakers, impersonate others, gain access to another person's files, or disrupt the service. Do not use its experimental outputs for consequential decisions about people, including admission, employment, or certification.</p>
    <h2>Availability and saved work</h2><p>The local prototype can stop, fail, or change during development. It is not a recording backup service. Keep your own permitted copies if needed. Use the deletion controls when you no longer need an attempt.</p>
    <h2>Third-party lessons</h2><p>Linked lessons belong to their respective providers. Their content and availability can change. Linking to a lesson does not imply endorsement or partnership.</p>
    <h2>Questions</h2><p>{contact_links(config)}</p>
    <p class="document-note">These terms describe the current local prototype. The team must review them with its final operator, hosting arrangements, and intended audience before public launch.</p>'''
    return page_html('Terms & Conditions', 'Use and limitations of the Accent Coach English pronunciation prototype.', body, '/terms')


def help_page():
    body = f'''<p class="eyebrow">A short practice session</p><h1>How Accent Coach works</h1>
    <p class="intro">Choose a sentence, record your voice, and review one practice sound. No reference recording is required.</p>
    <div class="how-grid" aria-label="Four steps to practice">
    <article class="how-card"><span class="how-number">01</span><h2>Choose</h2><p>Pick a sentence. Read its phonetic guide or listen to the synthetic English example.</p></article>
    <article class="how-card"><span class="how-number">02</span><h2>Record</h2><p>Use the microphone or upload a WAV. Keep your recording under five seconds and 10 MB.</p></article>
    <article class="how-card"><span class="how-number">03</span><h2>Analyze</h2><p>Press Check my recording. Demo processing may take a few moments, up to three minutes. The app shows the current stage.</p></article>
    <article class="how-card"><span class="how-number">04</span><h2>Feedback</h2><p>Review the recognized words and practice sound, replay your recording, and try again.</p></article>
    </div>
    <h2>What the result means</h2><div class="result-key">
    <div><span class="result-badge supported">Supported</span><p>The model favored the expected sound among the alternatives tested.</p></div>
    <div><span class="result-badge practice">Practice</span><p>The model favored a tested alternative. Listen again; the model can be mistaken.</p></div>
    <div><span class="result-badge inconclusive">Inconclusive</span><p>There is not enough reliable evidence for a useful sound comparison. This does not mean your pronunciation was wrong.</p></div>
    </div><p>These are experimental outcomes, not validated grades. The app checks selected contrasts in the words think, ship, and bad. The synthetic examples are optional listening aids and are never used for scoring.</p>
    <section class="troubleshooting" aria-labelledby="troubleshooting-title"><h2 id="troubleshooting-title">If something goes wrong</h2><details class="faq-item"><summary>No microphone</summary><p>Check your browser's microphone permission and selected input device. You can also upload a WAV.</p></details><details class="faq-item"><summary>Too quiet or noisy</summary><p>Record again in a quiet place, closer to the microphone.</p></details><details class="faq-item"><summary>Too loud</summary><p>Move slightly farther from the microphone and speak naturally.</p></details><details class="faq-item"><summary>Different recognized words</summary><p>Listen to the recording. Recognition may be wrong; try the selected sentence again.</p></details><details class="faq-item"><summary>Check timed out</summary><p>Press Record again. The next check uses a fresh worker.</p></details></section>
    <h2>Find an earlier attempt</h2><p>Open Saved attempts and refresh the list for the selected sentence. Choose an attempt to read its result or replay its audio. Deletion requires selecting the confirmation checkbox.</p>
    <p>Need help? {contact_links(load_site_config())}</p><a class="text-link" href="/">Start a practice session</a>'''
    return page_html('How it works', 'Recording instructions, result explanations, and troubleshooting for Accent Coach.', body, '/help')


def not_found_page():
    return page_html('Page not found', 'This Accent Coach page could not be found. Return to pronunciation practice.',
        '<p class="eyebrow">404</p><h1>Page not found</h1><p class="intro">This address does not lead to a page. Check the link or return to your practice session.</p><a class="text-link" href="/">Back to practice</a>', '/404', not_found=True)


def row_cards(headers, rows):
    if not rows:
        return '<p class="helper-text">No entries for this attempt.</p>'
    cards = []
    for row in rows:
        fields = []
        for label, value in zip(headers[1:], row[1:]):
            if isinstance(value, float):
                value = f'{value:.4g}'
            fields.append(f'<dt>{html.escape(str(label))}</dt><dd>{html.escape(str(value if value not in (None, "") else "Not available"))}</dd>')
        cards.append(f'<article class="detail-card"><h4>{html.escape(str(row[0]))}</h4><dl>{"".join(fields)}</dl></article>')
    return '<div class="detail-grid">' + ''.join(cards) + '</div>'


def measurement_cards(measurements):
    rows = []
    for key, value in measurements.items():
        if not value:
            continue
        if isinstance(value, dict):
            for field, item in value.items():
                if isinstance(item, (list, dict)):
                    item = f'{len(item)} entries. Full data in the results download.'
                rows.append([key.replace('_', ' '), field.replace('_', ' '), item])
    return row_cards(['Measurement', 'Field', 'Value'], rows)
