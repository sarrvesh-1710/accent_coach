"""Lesson invariants, evaluation denominators, storage safety, and worker recovery."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import multiprocessing as mp
import subprocess
import sys
import unittest
from unittest.mock import patch

import attempt_history as history
from analysis_service import AnalysisService
from lesson_catalog import load_lessons, validate_lessons
from tools.evaluate_recordings import decision_metrics, validate_splits
from speech_content import compare_transcript
from phoneme_scoring.process_lock import alignment_lock
from phoneme_scoring.align_audio import run_mfa

ROOT = Path(__file__).resolve().parents[1]


def echo_worker(requests, responses):
    while True:
        request = requests.get()
        if request[0] == 'hang':
            time.sleep(30)
        responses.put(('progress', 'Checking words'))
        responses.put(('result', {'input': request[0]}))


def hold_alignment(path, ready):
    with alignment_lock(path):
        ready.put(True)
        time.sleep(30)


class ReleaseTests(unittest.TestCase):
    def test_subprocess_timeout_cleans_up_then_next_call_succeeds(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run_mfa([sys.executable, '-c', 'import time; time.sleep(30)'], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=.25)
        self.assertEqual(run_mfa([sys.executable, '-c', 'pass'], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=10).returncode, 0)

    def test_alignment_lock_excludes_other_process_and_releases_after_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'alignment.lock'
            context = mp.get_context('spawn')
            ready = context.Queue()
            process = context.Process(target=hold_alignment, args=(path,ready))
            process.start()
            try:
                self.assertTrue(ready.get(timeout=10))
                with self.assertRaises(TimeoutError), alignment_lock(path, timeout=.2):
                    pass
            finally:
                process.terminate(); process.join(timeout=5); process.close()
                ready.close()
            with alignment_lock(path, timeout=.2):
                pass

    def test_all_twelve_lessons_are_configured_without_references(self):
        lessons = load_lessons(ROOT / 'prompts.json', require_practice=True)
        self.assertEqual(len(lessons), 12)
        for lesson in lessons:
            lesson.pop('reference_wav', None)
        self.assertEqual(len(validate_lessons(lessons, require_practice=True)), 12)

    def test_duplicate_and_missing_target_words_and_unsafe_links_are_rejected(self):
        original = load_lessons(ROOT / 'prompts.json')[0]
        for mutate in (lambda p: p.update(text='I think and think'),
                       lambda p: p.update(practice_words=[]),
                       lambda p: p.update(lesson_links=[{'title':'x','url':'javascript:bad'}]),
                       lambda p: p['assessment_targets'][0].update(alternatives=['TH'])):
            item = deepcopy(original)
            mutate(item)
            with self.assertRaises(ValueError):
                validate_lessons([item], require_practice=True)

    def test_content_difference_diagnostics_do_not_relax_gate(self):
        prompt = {'text':'I think so', 'content_alternatives':{'think':['sink']}}
        self.assertEqual(compare_transcript('I sink so', prompt)['status'], 'target_variant')
        diff = compare_transcript('I really think', prompt)
        self.assertEqual(diff['status'], 'mismatch')
        self.assertTrue(diff['word_differences'])

    def test_speaker_leakage_rejected(self):
        with self.assertRaises(ValueError):
            validate_splits([dict(id='a',speaker_id='S1',split='development'), dict(id='b',speaker_id='S1',split='held_out')])

    def test_metrics_count_uncertain_unreviewed_and_false_support(self):
        def row(label, state, reviewer='R1'):
            return dict(human_target_label=label, reviewer=reviewer, target_word='think', target_phone='TH',
                sequence_assessment={'targets':[dict(word='think',expected_phone='TH',status=state)]})
        metrics = decision_metrics([row('expected','expected_supported'),row('altered','expected_supported'),
                                    row('altered','insufficient_evidence'),row('expected','expected_supported','')])
        self.assertEqual(metrics['reviewed_clear'], 3)
        self.assertEqual(metrics['false_support'], 1)
        self.assertEqual(metrics['uncertain'], 1)
        self.assertEqual(metrics['unreviewed'], 1)
        self.assertEqual(metrics['coverage'], 2/3)
        self.assertEqual(metrics['agreement_on_decided'], .5)

    def test_history_deletes_only_selected_finished_folder(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(history, 'ROOT', Path(directory)):
            run_id = '20261011T120000_abcdef012345'
            folder = Path(directory) / run_id
            folder.mkdir()
            (folder / 'results.json').write_text(json.dumps(dict(run_id=run_id,prompt_id='think',audio_paths={'original':'outside.wav'})))
            (folder / 'learner.wav').write_bytes(b'local test')
            outside = Path(directory) / 'keep.txt'
            outside.write_text('keep')
            self.assertEqual(history.read_attempt(run_id)[1], str(folder/'learner.wav'))
            self.assertEqual(len(history.list_attempts('think')), 1)
            with self.assertRaises(ValueError):
                history.delete_attempt('../keep.txt')
            history.delete_attempt(run_id)
            self.assertFalse(folder.exists())
            self.assertTrue(outside.exists())

    def test_history_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(history, 'ROOT', Path(directory)):
            run_id = '20261011T120000_abcdef012345'
            outside = Path(directory)/'outside'
            outside.mkdir()
            try:
                (Path(directory)/run_id).symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('Creating symlinks is unavailable on this Windows installation')
            with self.assertRaises(ValueError):
                history.run_folder(run_id)

    def test_worker_reuses_process_and_recovers_after_timeout(self):
        service = AnalysisService(timeout_sec=10, worker_target=echo_worker)
        self.addCleanup(service.close)
        updates = []
        self.assertEqual(service.run('first','think',progress_callback=updates.append), {'input':'first'})
        pid = service.process.pid
        self.assertEqual(service.run('second','think'), {'input':'second'})
        self.assertEqual(service.process.pid, pid)
        self.assertEqual(updates, ['Checking words'])
        service.timeout_sec = .25
        with self.assertRaises(TimeoutError):
            service.run('hang','think')
        self.assertIsNone(service.process)
        service.timeout_sec = 10
        self.assertEqual(service.run('recovered','think'), {'input':'recovered'})

    def test_concurrent_service_call_is_rejected_without_second_worker(self):
        service = AnalysisService(worker_target=echo_worker)
        with service.lock, self.assertRaises(RuntimeError):
            service.run('x','think')
        self.assertIsNone(service.process)


if __name__ == '__main__':
    unittest.main()
