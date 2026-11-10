"""Create a new machine-local Windows MFA configuration without overwriting one.

No installation, download, model execution, or modification of shared settings.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from phoneme_scoring.persistent_mfa import runtime


def configuration(prefix,root=ROOT,environment=None):
    prefix=Path(prefix).resolve();root=Path(root).resolve()
    executable=prefix/'Scripts/mfa.exe'
    if not executable.is_file():raise ValueError('MFA executable is missing. Supply the MFA Conda environment prefix.')
    runtime([str(executable)])  # Retain the production version/runtime gate.
    environment=dict(os.environ if environment is None else environment)
    child={'CONDA_PREFIX':str(prefix),'PATH':os.pathsep.join([
        str(prefix),str(prefix/'Scripts'),str(prefix/'Library/bin'),str(prefix/'Library/usr/bin'),environment.get('PATH','')])}
    if environment.get('MFA_ROOT_DIR'):child['MFA_ROOT_DIR']=environment['MFA_ROOT_DIR']
    return dict(model=dict(cache_dir='../models/huggingface',local_files_only=True),
                mfa=dict(command=[str(executable)],environment=child,
                         dictionary_cache_directory=str(root/'runs/mfa_dictionary_resources')),
                mfa_execution=dict(reuse_process=True,idle_sec=600,reuse_lexicon_graphs=True))


def write_new(destination,value):
    # Exclusive creation also prevents a race from replacing existing settings.
    with Path(destination).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix',required=True,help='Absolute Windows MFA 3.3.7 Conda prefix')
    parser.add_argument('--output',type=Path,default=ROOT/'phoneme_scoring/settings.local.json')
    args=parser.parse_args()
    if os.name!='nt':parser.error('This helper configures the existing Windows fast path, not a Linux port.')
    try:write_new(args.output,configuration(args.prefix))
    except (OSError,ValueError) as exc:parser.exit(1,f'Configuration not written: {exc}\n')
    print('Created machine-local MFA settings. Existing shared model settings were not changed.')


if __name__=='__main__':main()
