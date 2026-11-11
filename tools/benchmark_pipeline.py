"""Serial backend benchmark using existing stage timers; no model behavior changes."""
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis_service import AnalysisService

def main():
    destination = ROOT / 'runs' / ('phase3-baseline-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
    report = dict(started_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(), platform=platform.platform(),
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        benchmark_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        versions={p:importlib.metadata.version(p) for p in ['torch','transformers','gradio','numpy','scipy']},
        source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['analysis_service.py','pipeline.py','speech_content.py','phoneme_scoring/align_audio.py','phoneme_scoring/gop_score.py','phoneme_scoring/sequence_evidence.py','phoneme_scoring/settings.json','phoneme_scoring/settings.local.json'] if (ROOT/name).exists()},
        scope='Direct AnalysisService.run wall time including fresh-worker start, result saving and return. Excludes launcher imports, browser upload, UI queue/rendering. Fresh worker is not cold OS disk cache. Synthetic audio used as learner input; references disabled.',
        missing_measurements=['Model loading versus inference within stages','MFA lock wait versus subprocess startup versus alignment','Feedback and saving individually','Browser end-to-end latency','Server startup to readiness'],
        retries=0,cases=[])
    print('Report: '+str(destination),flush=True)
    for lesson in ['think','ship','bad_bed']:
        service=AnalysisService()
        try:
            for repeat in range(3):
                path=ROOT/'web_assets/examples'/f'{lesson}.wav'
                with wave.open(str(path),'rb') as audio:
                    duration=audio.getnframes()/audio.getframerate()
                row=dict(lesson=lesson,repeat=repeat+1,condition='fresh_worker' if repeat==0 else 'reused_worker',duration_sec=duration,
                         audio_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),retry=False)
                started=time.monotonic()
                try:
                    r=service.run(str(path),lesson,compare_reference=False)
                    row.update(wall_sec=round(time.monotonic()-started,4),timings_sec=r.get('timings_sec',{}),
                        overall_status=r.get('overall_status'),content_status=r.get('spoken_words_verification',{}).get('status'),
                        alignment_status=r.get('alignment',{}).get('status'),scoring_status=r.get('phoneme_results',{}).get('status'),
                        sequence_status=r.get('phoneme_results',{}).get('sequence_evidence',{}).get('status'),
                        target_statuses=[t['status'] for t in r.get('target_assessment',{}).get('targets',[])],
                        run_id=r.get('run_id'),stages=r.get('stage_statuses',{}),reference_requested=r.get('reference_comparison_requested'))
                    row['full_path_completed']=(row['content_status'] in ['match','target_variant'] and row['alignment_status']=='available'
                        and row['sequence_status']=='available' and r.get('stage_statuses',{}).get('save',{}).get('status')=='ok')
                except Exception as exc:
                    row.update(wall_sec=round(time.monotonic()-started,4),error=f'{type(exc).__name__}: {exc}',full_path_completed=False)
                report['cases'].append(row)
                destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
                print(json.dumps(row),flush=True)
                # The first case verifies real processing before proceeding with the study.
                if not row['full_path_completed']:
                    print('Stopping: failed/incomplete processing; no automatic retries.',flush=True)
                    return 1
        finally:
            service.close()
    print('Completed all nine runs: '+str(destination),flush=True)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
