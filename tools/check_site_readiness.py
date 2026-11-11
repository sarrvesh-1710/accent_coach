"""Report launch requirements without publishing or claiming domain verification."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from site_pages import load_site_config


def main():
    config = load_site_config()
    report = {
        'local_frontend_configured': True,
        'team': config['owner'],
        'contact_email': config.get('email'),
        'public_url': config.get('public_url'),
        'favicon_present': (ROOT / 'web_assets/favicon.ico').is_file(),
        'policy_pages_present': True,
        'policies_reviewed_for_public_launch': config.get('policies_reviewed_for_public_launch', False),
        'public_launch_ready': False,
        'remaining': [
            'Choose and connect an owned custom domain to the selected host, then verify HTTPS and DNS.',
            'Review policy wording against the final hosting, retention, audience, and operator arrangements.',
            'Provide authenticated, isolated user recording storage before public multi-user access.',
            'Test recording permissions, analysis, playback, and deletion on actual target devices.'
        ],
        'note': 'The app remains bound to localhost. A configured URL alone does not verify a live domain.'
    }
    destination = ROOT / 'runs/site_readiness.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
