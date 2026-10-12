"""Record exact source hashes, dependency versions, and model revisions for a demo."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phoneme_scoring.align_audio import load_settings


def main():
    files = [*ROOT.glob('*.py'), *ROOT.glob('*.json'), *ROOT.glob('requirements*.txt'),
             *(ROOT / 'phoneme_scoring').glob('*.py'), ROOT / 'phoneme_scoring/settings.json',
             ROOT / 'phoneme_scoring/phoneme_map.json', *(ROOT / 'tests').glob('*.py'), *(ROOT / 'tools').glob('*.py'),
             *[p for p in (ROOT / 'web_assets').rglob('*') if p.is_file()]]
    settings = load_settings(ROOT / 'phoneme_scoring/settings.json')
    report = dict(git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
                  python=sys.version, dependencies={d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
                  models={k: settings[k] for k in ('model', 'content_check')},
                  note='Local working-copy snapshot; hashes include uncommitted code. Recordings and secrets excluded.')
    destination = ROOT / 'runs/demo_release.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(destination)


if __name__ == '__main__':
    main()
