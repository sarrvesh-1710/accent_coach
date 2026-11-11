"""Export actual recent target intervals and recognizer disagreements for human review."""
import csv
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import attempt_history

def main():
    destination = ROOT / 'runs/alignment_review.csv'
    fields = ['run_id','sentence','recognized_words','content_status','word','phone','start_sec','end_sec',
              'outcome','margin_nats','interval_inside_audio','audio_path','human_boundary_label','human_sound_label','reviewer']
    rows = []
    for _, identity in attempt_history.list_attempts(limit=50):
        result, audio = attempt_history.read_attempt(identity)
        duration = result.get('learner_audio', {}).get('duration_sec')
        for row in result.get('target_assessment', {}).get('targets', []):
            start, end = row.get('start_sec'), row.get('end_sec')
            valid = isinstance(start,(int,float)) and isinstance(end,(int,float)) and isinstance(duration,(int,float)) and 0 <= start < end <= duration + 1e-6
            rows.append(dict(run_id=identity, sentence=result.get('prompt',{}).get('text'),
                recognized_words=result.get('spoken_words_verification',{}).get('transcript'),
                content_status=result.get('spoken_words_verification',{}).get('status'), word=row['word'],phone=row['expected_phone'],
                start_sec=start,end_sec=end,outcome=row['status'],margin_nats=row.get('margin_nats'),
                interval_inside_audio=valid,audio_path=audio,human_boundary_label='',human_sound_label='',reviewer=''))
    with destination.open('w',newline='',encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    print(f'{len(rows)} target intervals exported to {destination}. Blank human labels are intentional; bounds checks do not validate alignment.')

if __name__ == '__main__':
    main()
