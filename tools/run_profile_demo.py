"""Local presentation workspace; illustrative history stays separate from real users."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def seed(store):
    password='demo-practice-403!'
    if not store.login('demo_assessment',password):
        store.register('demo_assessment',password,'Starting Check Demo')
    if not store.login('demo_starter',password):
        store.register('demo_starter',password,'Starter Learner',background=dict(language='japanese',use_starters=True))
    owner=store.login('demo_learner',password)
    if owner:return
    owner=store.register('demo_learner',password,'Demo Learner')
    store.profile(owner,'Demo Learner',['TH','IH'])
    examples=[('think','TH','practice',0),('ship','IH','inconclusive',1),('bad_bed','AE','supported',2),
              ('think','TH','practice',3),('ship','IH','supported',4)]
    prompts={p['id']:p for p in json.loads((ROOT/'prompts.json').read_text(encoding='utf-8'))}
    for lesson,phone,outcome,days in examples:
        prompt=prompts[lesson]
        identity=store.create_attempt(owner,prompt,(ROOT/'web_assets/examples'/f'{lesson}.wav').read_bytes())
        status={'practice':'alternative_favored','supported':'expected_supported','inconclusive':'insufficient_evidence'}[outcome]
        result=dict(overall_status='completed',demo_sample=True,
            spoken_words_verification=dict(transcript=prompt['text']),
            target_assessment=dict(targets=[dict(word=prompt['target_words'][0],expected_phone=phone,status=status)]),
            stage_statuses={'source':'Illustrative demo sample; not measured speech.'})
        store.finish(owner,identity,result=result)
        with store.connect() as db:
            db.execute('UPDATE attempts SET sentence=?,created=? WHERE id=?',('[Sample] '+prompt['text'],time.time()-days*86400,identity))
    store.register('demo_new',password,'New Learner')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=7864)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    from accounts.store import Store
    folder=ROOT/'runs/profile_demo'
    seed(Store(folder))
    os.environ['ACCENT_COACH_DATA_DIR']=str(folder)
    os.environ['ACCENT_COACH_DEMO']='1'
    os.environ['GRADIO_SERVER_PORT']=str(args.port)
    os.environ['ACCENT_COACH_OPEN_BROWSER']='0' if args.no_browser else '1'
    print('Sample workspace only. Username: demo_learner  Password: demo-practice-403!',flush=True)
    print('Use demo_starter with the same password for editable language-based starter lessons.',flush=True)
    print('Use demo_assessment with the same password for the three-sentence starting check.',flush=True)
    print('Use demo_new with the same password to show the empty starting profile.',flush=True)
    from site_server import serve
    serve()


if __name__=='__main__':main()
