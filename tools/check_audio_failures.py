"""Deterministic quiet/noise controls. Not a general noise-robustness benchmark."""
import json
from pathlib import Path
import sys
import numpy as np
import soundfile as sf
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis_service import AnalysisService

def main():
    folder = ROOT/'runs/synthetic_lessons'
    folder.mkdir(parents=True, exist_ok=True)
    controls = {'very_quiet': 1e-7 * np.sin(np.arange(32000)*.08),
                'white_noise': np.clip(np.random.default_rng(403).normal(0,.08,32000),-.9,.9)}
    rows = []
    service = AnalysisService()
    try:
        for name, audio in controls.items():
            path = folder/(name+'.wav')
            sf.write(path,audio,16000,subtype='FLOAT')
            r = service.run(str(path),'think')
            passed = all(t['status'] == 'insufficient_evidence' for t in r['target_assessment']['targets'])
            rows.append(dict(case=name,pass_guard=passed,content=r['spoken_words_verification'],result_path=r['results_path']))
            print(name, passed, flush=True)
    finally:
        service.close()
    (ROOT/'runs/audio_failure_checks.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    return int(not all(r['pass_guard'] for r in rows))

if __name__ == '__main__':
    raise SystemExit(main())
