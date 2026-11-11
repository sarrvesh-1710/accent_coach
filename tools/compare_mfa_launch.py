"""Controlled local launcher experiment; never edits alignment settings."""
from copy import deepcopy
import json
import os
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from phoneme_scoring.align_audio import align_audio,load_settings


def main():
    settings=load_settings(ROOT/'phoneme_scoring/settings.json')
    envroot=Path.home()/'anaconda3/envs/accent-coach-mfa'
    direct=envroot/'Scripts/mfa.exe'
    if not direct.is_file():raise RuntimeError('Installed direct MFA executable unavailable')
    os.environ['PATH']=os.pathsep.join(str(envroot/p) for p in ('','Scripts','Library/bin','Library/usr/bin'))+os.pathsep+os.environ['PATH']
    os.environ['CONDA_PREFIX']=str(envroot)
    settings['mfa']['command']=[str(Path.home()/'anaconda3/Scripts/conda.exe'),'run','--no-capture-output','-n','accent-coach-mfa','mfa']
    settings['mfa'].pop('environment',None)
    root=ROOT/'runs/mfa-launch-comparison';root.mkdir(exist_ok=True)
    rows=[];fields=('segments','words','audio_sha256','duration_sec','sample_rate_hz')
    for repeat in range(3):
        expected=None
        for kind in ('conda','direct'):
            cfg=deepcopy(settings)
            if kind=='direct':cfg['mfa']['command']=[str(direct)]
            result=align_audio(ROOT/'web_assets/examples/think.wav','I think so',cfg,root/f'{repeat}-{kind}')
            row=dict(repeat=repeat+1,launcher=kind,status=result['status'],timings_sec=result['timings_sec'])
            if kind=='conda':expected={k:result.get(k) for k in fields}
            else:row['same_alignment']=result['status']=='available' and expected=={k:result.get(k) for k in fields}
            rows.append(row)
            (root/'measurements.json').write_text(json.dumps(rows,indent=2))
            print(json.dumps(row),flush=True)
            if result['status']!='available' or row.get('same_alignment') is False:return 1
    print(json.dumps({k:statistics.median(r['timings_sec']['total'] for r in rows if r['launcher']==k) for k in ('conda','direct')}),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
