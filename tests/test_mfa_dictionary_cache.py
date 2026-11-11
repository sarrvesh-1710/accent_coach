"""Resource identity/atomic-copy tests; fixture resources, no MFA inference."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from phoneme_scoring import mfa_dictionary_cache as cache


class DictionaryCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp)
        env = self.root / 'env'
        (env / 'Scripts').mkdir(parents=True)
        (env / 'Scripts/mfa.exe').write_bytes(b'fixture-executable')
        (env / 'conda-meta').mkdir()
        self.metadata = env / 'conda-meta/montreal-forced-aligner-3.3.7-test.json'
        self.metadata.write_text(json.dumps({'version': '3.3.7'}))
        self.mfa_root = self.root / 'MFA'
        (self.mfa_root / 'pretrained_models/dictionary').mkdir(parents=True)
        (self.mfa_root / 'pretrained_models/acoustic').mkdir()
        self.dictionary = self.mfa_root / 'pretrained_models/dictionary/english_us_arpa.dict'
        self.model = self.mfa_root / 'pretrained_models/acoustic/english_us_arpa.zip'
        self.dictionary.write_text('think TH IH1 NG K\n')
        self.model.write_bytes(b'fixture-model')
        self.cfg = dict(command=[str(env / 'Scripts/mfa.exe')], dictionary='english_us_arpa',
                        acoustic_model='english_us_arpa', dictionary_cache_directory=str(self.root / 'cache'),
                        environment={'MFA_ROOT_DIR': str(self.mfa_root)})

    def resources(self, plan, directory):
        folder = cache.request_dictionary(plan, directory)
        folder.mkdir(parents=True)
        for name in cache.FILES:
            (folder / name).write_bytes(('fixture-' + name).encode())
        return folder

    def build(self):
        plan = cache.plan(self.cfg)
        folder = self.resources(plan, self.root / 'build')
        self.assertTrue(cache.publish(plan, self.root / 'build'))
        return plan, folder

    def test_resource_reuse_across_distinct_requests_never_caches_audio_or_results(self):
        plan, folder = self.build()
        (folder / 'learner.wav').write_bytes(b'private-audio')
        (folder / 'clip.lab').write_text('private-transcript')
        self.assertEqual({p.name for p in plan['entry'].iterdir()}, set(cache.FILES) | {'manifest.json'})
        for request in ('different-audio-a', 'different-audio-b'):
            destination = self.root / request
            self.assertTrue(cache.seed(plan, destination))
            seeded = cache.request_dictionary(plan, destination)
            self.assertEqual((seeded / 'L.fst').read_bytes(), (folder / 'L.fst').read_bytes())
            # Real copies, not hardlinks into shared mutable resources.
            (seeded / 'L.fst').write_bytes(b'request-only-change')
            self.assertEqual((plan['entry'] / 'L.fst').read_bytes(), b'fixture-L.fst')

    def test_content_runtime_profile_and_configuration_changes_invalidate(self):
        original = cache.plan(self.cfg)['key']
        self.dictionary.write_text('think S IH1 NG K\n')
        self.assertNotEqual(original, cache.plan(self.cfg)['key'])
        current = cache.plan(self.cfg)['key']; self.model.write_bytes(b'changed-model')
        self.assertNotEqual(current, cache.plan(self.cfg)['key'])
        current = cache.plan(self.cfg)['key']; self.metadata.write_text(json.dumps({'version': '3.3.7', 'build': 'new'}))
        self.assertNotEqual(current, cache.plan(self.cfg)['key'])
        current = cache.plan(self.cfg)['key']; (self.mfa_root / 'global_config.yaml').write_text('clean: false\n')
        self.assertNotEqual(current, cache.plan(self.cfg)['key'])
        current = cache.plan(self.cfg)['key']; self.cfg['environment']['MFA_PROFILE'] = 'other'
        self.assertNotEqual(current, cache.plan(self.cfg)['key'])

    def test_corrupt_incomplete_or_wrong_manifest_falls_back_without_partial_seed(self):
        plan, _ = self.build()
        manifest = plan['entry'] / 'manifest.json'
        original = manifest.read_bytes()
        for contents in (b'{', b'{}', b'[]', b'null', b'1', b'"invalid"',
                         b'{"key":"wrong","files":{}}'):
            manifest.write_bytes(contents)
            self.assertFalse(cache.seed(plan, self.root / 'request'))
        manifest.write_bytes(original)
        (plan['entry'] / 'L.fst').write_bytes(b'corrupt')
        self.assertFalse(cache.seed(plan, self.root / 'request'))
        self.assertFalse(cache.request_dictionary(plan, self.root / 'request').exists())
        self.assertFalse(cache.publish(plan, self.root / 'build'))  # Preserve corrupt entry for inspection.

    def test_copy_failure_does_not_leave_active_partial_dictionary(self):
        plan, _ = self.build()
        original = cache.shutil.copyfile
        def fail_second(source, destination):
            if Path(source).name == 'L_align.fst':
                raise OSError('simulated disk error')
            return original(source, destination)
        with patch.object(cache.shutil, 'copyfile', side_effect=fail_second):
            self.assertFalse(cache.seed(plan, self.root / 'request'))
        self.assertFalse(cache.request_dictionary(plan, self.root / 'request').exists())

    def test_incomplete_build_is_never_published(self):
        plan = cache.plan(self.cfg)
        folder = self.resources(plan, self.root / 'build')
        (folder / 'phones.txt').unlink()
        self.assertFalse(cache.publish(plan, self.root / 'build'))
        self.assertFalse(plan['entry'].exists())

    def test_unsupported_runtime_or_launcher_rejected_for_normal_fallback(self):
        self.metadata.write_text(json.dumps({'version': '3.4.0'}))
        with self.assertRaises(ValueError): cache.plan(self.cfg)
        self.cfg['command'] = ['conda', 'run', 'mfa']
        with self.assertRaises(ValueError): cache.plan(self.cfg)
        self.cfg['dictionary_cache_directory'] = '../relative-cache'
        with self.assertRaises(ValueError): cache.plan(self.cfg)


if __name__ == '__main__':
    unittest.main()
