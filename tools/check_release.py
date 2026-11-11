"""Offline operational checks: synthetic lessons and invalid input. Not an accuracy benchmark."""
import json
from pathlib import Path
import sys
import time
import argparse
import numpy as np
import soundfile as sf
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis_service import AnalysisService
from pipeline import load_prompts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume', action='store_true', help='Keep completed passing checks; rerun failed or unfinished checks with a fresh worker.')
    args = parser.parse_args()
    folder = ROOT / 'runs/synthetic_lessons'
    folder.mkdir(parents=True, exist_ok=True)
    sf.write(folder/'silence.wav', np.zeros(16000), 16000)
    sf.write(folder/'too_long.wav', np.zeros(96000), 16000)
    sf.write(folder/'clipping.wav', np.sign(np.sin(np.arange(32000) * .08)), 16000)
    (folder/'invalid.wav').write_text('This is not audio.')
    destination = ROOT/'runs/release_smoke.json'
    service = AnalysisService()
    rows = json.loads(destination.read_text(encoding='utf-8'))['cases'] if args.resume and destination.exists() else []
    completed = {r['case'] for r in rows if r['status'] == 'pass'}
    rows = [r for r in rows if r['status'] == 'pass']
    cases = [(p['id'], folder/(p['id']+'.wav'), p['id'], 'synthetic_speech') for p in load_prompts()]
    cases.extend((name, folder/(name+'.wav'), 'think', 'unusable') for name in ('silence','too_long','invalid','clipping'))
    cases.append(('wrong_sentence',folder/'think.wav','ship','mismatch'))
    partner = ROOT/'runs/20260929T143731_68aed8db2fee/learner.wav'
    if partner.exists():
        cases.append(('partner_think',partner,'think','real_unlabeled_speech'))
    try:
        for name, path, prompt_id, kind in cases:
            if name in completed:
                continue
            if not path.exists():
                rows.append(dict(case=name,status='not_run',reason='Synthetic lesson audio must be prepared locally.'))
                continue
            start = time.monotonic()
            try:
                r = service.run(str(path),prompt_id)
                targets = r['target_assessment']['targets']
                sound_states = [t['status'] for t in targets]
                guarded = all(s == 'insufficient_evidence' for s in sound_states)
                content = r['spoken_words_verification'].get('status')
                if kind == 'unusable':
                    passed = guarded
                elif kind == 'mismatch':
                    passed = content == 'mismatch' and guarded and r['stage_statuses']['alignment']['status'] == 'skipped'
                else:
                    passed = (content == 'mismatch' and guarded) or (
                        content in {'match','target_variant'} and r['alignment'].get('status') == 'available' and
                        r['phoneme_results'].get('sequence_evidence',{}).get('status') == 'available')
                passed = passed and r['audio_paths']['reference'] is None and r['results_path'] is not None
                rows.append(dict(case=name,status='pass' if passed else 'fail',input_kind=kind,
                    seconds=round(time.monotonic()-start,2),content_status=content,
                    recognized=r['spoken_words_verification'].get('transcript'),sound_states=sound_states,
                    result_path=r['results_path'],timings_sec=r.get('timings_sec',{})))
            except Exception as exc:
                rows.append(dict(case=name,status='fail',error=str(exc),seconds=round(time.monotonic()-start,2)))
            destination.write_text(json.dumps({'note':'Operational outcomes only. Synthetic audio is not human pronunciation validation.', 'cases':rows},indent=2),encoding='utf-8')
            print(json.dumps(rows[-1]),flush=True)
    finally:
        service.close()
    return 1 if any(r['status'] != 'pass' for r in rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
