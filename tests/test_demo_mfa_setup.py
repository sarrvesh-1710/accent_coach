"""Setup-file safety with fake Conda metadata; no MFA execution or downloads."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.configure_demo_mfa import configuration,write_new


class DemoMFASetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.prefix=self.root/'mfa-env'
        (self.prefix/'Scripts').mkdir(parents=True);(self.prefix/'conda-meta').mkdir()
        (self.prefix/'python.exe').write_bytes(b'fixture, not executable')
        (self.prefix/'Scripts/mfa.exe').write_bytes(b'fixture, not executable')
        self.metadata=self.prefix/'conda-meta/montreal-forced-aligner-fixture.json'
        self.metadata.write_text(json.dumps({'version':'3.3.7'}),encoding='utf-8')

    def test_portable_settings_recreate_fast_path_from_the_new_machine(self):
        value=configuration(self.prefix,self.root,dict(PATH='fixture-path',MFA_ROOT_DIR='fixture-model-root'))
        self.assertEqual(value['mfa']['command'],[str(self.prefix/'Scripts/mfa.exe')])
        self.assertEqual(value['mfa']['environment']['CONDA_PREFIX'],str(self.prefix))
        self.assertEqual(value['mfa']['environment']['MFA_ROOT_DIR'],'fixture-model-root')
        self.assertEqual(value['mfa_execution'],dict(reuse_process=True,idle_sec=600,reuse_lexicon_graphs=True))
        self.assertTrue(value['mfa']['environment']['PATH'].endswith('fixture-path'))

    def test_wrong_runtime_or_missing_executable_is_rejected(self):
        self.metadata.write_text(json.dumps({'version':'3.3.6'}),encoding='utf-8')
        with self.assertRaises(ValueError):configuration(self.prefix,self.root,{})
        (self.prefix/'Scripts/mfa.exe').unlink()
        with self.assertRaises(ValueError):configuration(self.prefix,self.root,{})

    def test_existing_settings_are_never_overwritten(self):
        target=self.root/'settings.local.json';target.write_text('preserve existing data',encoding='utf-8')
        with self.assertRaises(FileExistsError):write_new(target,{'replace':True})
        self.assertEqual(target.read_text(encoding='utf-8'),'preserve existing data')

    def test_new_settings_are_utf8_json_without_bom(self):
        target=self.root/'settings.local.json';value=configuration(self.prefix,self.root,{})
        write_new(target,value)
        self.assertFalse(target.read_bytes().startswith(b'\xef\xbb\xbf'))
        self.assertEqual(json.loads(target.read_text(encoding='utf-8')),value)


if __name__=='__main__':unittest.main()
