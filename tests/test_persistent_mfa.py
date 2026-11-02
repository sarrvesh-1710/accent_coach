"""Real private-pipe/process lifecycle tests with a tiny fake MFA worker.

No real MFA/model inference here. Real-engine parity is benchmarked separately.
"""
import importlib
import json
import os
import pstats
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from phoneme_scoring import persistent_mfa as reuse


STUB='''import json,sys,time
print(json.dumps({'event':'ready','startup_sec':.125}),flush=True)
for line in sys.stdin:
    request=json.loads(line)
    mode=request['args'][1]
    if mode=='hang':time.sleep(60)
    if mode=='crash':sys.exit(3)
    if mode=='malformed':print('invalid-json',flush=True);continue
    print(json.dumps({'id':'wrong' if mode=='wrong' else request['id'],
        'returncode':1 if mode=='fail' else 0,'execution_sec':.01}),flush=True)
'''


class PersistentMFATests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.stub=self.root/'worker.py';self.stub.write_text(STUB)
        self.log=self.enterContext((self.root/'mfa.log').open('w'))
        self.addCleanup(reuse.close_all)

    def client(self):
        client=reuse.Client(sys.executable,os.environ.copy(),worker_script=self.stub)
        self.addCleanup(client.close)
        return client

    def test_reuses_only_process_and_retains_request_arguments(self):
        client=self.client();pid=client.process.pid
        first=client.run(['mfa.exe','align_one','one'],self.log.name,10)
        second=client.run(['mfa.exe','align_one','different-audio'],self.log.name,10)
        self.assertEqual(first.returncode,0)
        self.assertEqual(second.args,['mfa.exe','align_one','different-audio'])
        self.assertEqual(second.execution_info['pid'],pid)
        self.assertFalse(first.execution_info['reused'])
        self.assertTrue(second.execution_info['reused'])
        self.assertEqual(first.execution_info['startup_sec'],.125)
        self.assertEqual(second.execution_info['startup_sec'],0)

    def test_timeout_kills_owned_process_then_new_client_can_work(self):
        client=self.client()
        with self.assertRaises(subprocess.TimeoutExpired):
            client.run(['mfa.exe','align_one','hang'],self.log.name,.3)
        self.assertIsNotNone(client.process.poll())
        next_client=self.client()
        self.assertEqual(next_client.run(['mfa.exe','align_one','okay'],self.log.name,10).returncode,0)

    def test_actual_failed_alignment_closes_poisoned_process(self):
        client=self.client()
        result=client.run(['mfa.exe','align_one','fail'],self.log.name,10)
        self.assertEqual(result.returncode,1)
        self.assertIsNotNone(client.process.poll())

    def test_wrong_identity_malformed_response_and_crash_never_succeed(self):
        for mode in ['wrong','malformed','crash']:
            with self.subTest(mode=mode):
                client=self.client()
                with self.assertRaises(RuntimeError):
                    client.run(['mfa.exe','align_one',mode],self.log.name,10)
                self.assertIsNotNone(client.process.poll())

    def test_busy_request_does_not_enter_private_protocol(self):
        client=self.client()
        with client.lock:
            with self.assertRaises(RuntimeError):
                client.run(['mfa.exe','align_one','okay'],self.log.name,10)
        self.assertEqual(client.calls,0)

    def test_runtime_gate_rejects_unverified_or_different_install(self):
        prefix=self.root/'mfa-env';(prefix/'Scripts').mkdir(parents=True)
        (prefix/'conda-meta').mkdir();(prefix/'python.exe').write_bytes(b'fixture')
        metadata=prefix/'conda-meta/montreal-forced-aligner-fixture.json'
        metadata.write_text(json.dumps({'version':'3.3.7'}))
        command=[str(prefix/'Scripts/mfa.exe')]
        self.assertEqual(reuse.runtime(command)[0],prefix/'python.exe')
        for contents in ['{"version":"3.4.0"}','null','{']:
            metadata.write_text(contents)
            with self.assertRaises(reuse.UnsupportedRuntime):reuse.runtime(command)
        with self.assertRaises(reuse.UnsupportedRuntime):reuse.runtime(['conda','run','mfa'])

    def test_idle_retention_rejects_invalid_values_before_launch(self):
        with patch.object(reuse,'runtime') as runtime,patch.object(reuse,'Client') as client:
            for value in [None,True,0,29,601,120.0,'600']:
                with self.subTest(value=value),self.assertRaises(ValueError):
                    reuse.run(['mfa.exe','align_one','okay'],stdout=self.log,timeout=10,idle_sec=value)
            runtime.assert_not_called();client.assert_not_called()

    def test_retention_setting_reuses_same_client_and_replaces_changed_policy(self):
        real_client=reuse.Client
        def fixture_client(python,env,**kwargs):
            return real_client(python,env,worker_script=self.stub,**kwargs)
        args=['mfa.exe','align_one','okay']
        with patch.object(reuse,'runtime',return_value=(Path(sys.executable),'fixture-version')),patch.object(reuse,'Client',side_effect=fixture_client) as factory:
            first=reuse.run(args,stdout=self.log,timeout=10,idle_sec=600)
            same=reuse.run(args,stdout=self.log,timeout=10,idle_sec=600)
            previous=next(iter(reuse._clients.values()))
            changed=reuse.run(args,stdout=self.log,timeout=10,idle_sec=120)
            self.assertEqual(first.execution_info['pid'],same.execution_info['pid'])
            self.assertTrue(same.execution_info['reused'])
            self.assertIsNotNone(previous.process.poll())
            self.assertNotEqual(first.execution_info['pid'],changed.execution_info['pid'])
            self.assertEqual([c.kwargs['idle_sec'] for c in factory.call_args_list],[600,120])

    def test_actual_worker_protocol_retains_process_then_exits_on_idle(self):
        # Execute our real worker lifecycle with a tiny import-compatible CLI,
        # not the real MFA engine. No model or alignment accuracy claim.
        package=self.root/'montreal_forced_aligner';command=package/'command_line'
        command.mkdir(parents=True)
        for file in [package/'__init__.py',command/'__init__.py',package/'config.py']:
            file.write_text('')
        (command/'utils.py').write_text('class ExitHooks: pass\n')
        (command/'mfa.py').write_text('class CLI:\n def main(self,**kwargs): pass\nmfa_cli=CLI()\n')
        env={**os.environ,'PYTHONPATH':str(self.root)}
        client=reuse.Client(sys.executable,env,worker_script=Path(reuse.__file__).with_name('mfa_worker.py'),idle_sec=.6)
        self.addCleanup(client.close)
        first=client.run(['mfa.exe','align_one','one'],self.log.name,10)
        with self.assertRaises(subprocess.TimeoutExpired):client.process.wait(timeout=.1)
        second=client.run(['mfa.exe','align_one','different-audio'],self.log.name,10)
        self.assertEqual(first.execution_info['pid'],second.execution_info['pid'])
        self.assertTrue(second.execution_info['reused'])
        self.assertEqual(client.process.wait(timeout=5),0)

    def test_actual_worker_profiles_only_requested_cli_call(self):
        package=self.root/'montreal_forced_aligner';command=package/'command_line'
        command.mkdir(parents=True)
        for file in [package/'__init__.py',command/'__init__.py',package/'config.py']:
            file.write_text('')
        (command/'utils.py').write_text('class ExitHooks: pass\n')
        (command/'mfa.py').write_text('class CLI:\n def main(self,**kwargs): sum(range(100))\nmfa_cli=CLI()\n')
        client=reuse.Client(sys.executable,{**os.environ,'PYTHONPATH':str(self.root)},
            worker_script=Path(reuse.__file__).with_name('mfa_worker.py'),idle_sec=1)
        self.addCleanup(client.close)
        output=Path(self.log.name).with_suffix('.pstats')
        normal=client.run(['mfa.exe','align_one','secret-utterance'],self.log.name,10)
        self.assertFalse(output.exists())
        # No kalpy is installed in the tiny CLI fixture: opt-in reuse must fall
        # back to its original CLI rather than fail this otherwise valid job.
        fallback=client.run(['mfa.exe','align_one','secret-utterance'],self.log.name,10,reuse_graphs=True)
        self.assertEqual(fallback.returncode,0)
        profiled=client.run(['mfa.exe','align_one','secret-utterance'],self.log.name,10,profile=True)
        self.assertEqual(normal.returncode,profiled.returncode)
        self.assertTrue(profiled.execution_info['profiled'])
        self.assertTrue(profiled.execution_info['reused'])
        functions=repr(pstats.Stats(str(output)).stats)
        self.assertIn('main',functions)
        self.assertNotIn('secret-utterance',functions)
        output.unlink();output.mkdir()  # Make diagnostic dump fail safely.
        failed_dump=client.run(['mfa.exe','align_one','secret-utterance'],self.log.name,10,profile=True)
        self.assertEqual(failed_dump.returncode,0)
        self.assertNotIn('profiled',failed_dump.execution_info)

    def test_registry_restarts_dead_child_and_changes_environment_safely(self):
        real_client=reuse.Client
        def fixture_client(python,env,**kwargs):
            return real_client(python,env,worker_script=self.stub,**kwargs)
        args=['mfa.exe','align_one','okay']
        with patch.object(reuse,'runtime',return_value=(Path(sys.executable),'fixture-version')),patch.object(reuse,'Client',side_effect=fixture_client):
            first=reuse.run(args,stdout=self.log,timeout=10,env=os.environ.copy())
            client=next(iter(reuse._clients.values()));client.close()
            second=reuse.run(args,stdout=self.log,timeout=10,env=os.environ.copy())
            self.assertNotEqual(first.execution_info['pid'],second.execution_info['pid'])
            previous=next(iter(reuse._clients.values()))
            third=reuse.run(args,stdout=self.log,timeout=10,env={**os.environ,'ACCENT_TEST_RUNTIME':'different'})
            self.assertIsNotNone(previous.process.poll())
            self.assertNotEqual(second.execution_info['pid'],third.execution_info['pid'])

    def test_alignment_dispatch_remains_inside_existing_lock(self):
        from contextlib import contextmanager
        import numpy as np
        module=importlib.import_module('phoneme_scoring.align_audio')
        held=[]
        @contextmanager
        def lock(*args):
            held.append(True)
            try:yield
            finally:held.pop()
        def execute(args,**kwargs):
            self.assertTrue(held)
            self.assertEqual(args[1],'align_one')
            self.assertEqual(kwargs['timeout'],120)
            Path(args[6]).write_text('fixture')
            result=subprocess.CompletedProcess(args,0)
            result.execution_info={'mode':'persistent','reused':True}
            return result
        settings={'mfa_execution':{'reuse_process':True},'mfa':{'executable':'mfa.exe',
            'dictionary':'dict','acoustic_model':'model','phone_tiers':['phones'],'timeout_sec':120}}
        with patch.object(module,'prepare_audio',return_value=(np.ones(16000)*.1,16000,'same-audio')),patch.object(module,'alignment_lock',side_effect=lock),patch.object(reuse,'run',side_effect=execute),patch.object(module,'parse_textgrid',return_value={'phones':[(0,1,'TH')],'words':[(0,1,'think')]}):
            result=module.align_audio('fixture','think',settings,self.root)
        self.assertEqual(result['status'],'available')
        self.assertEqual(result['audio_sha256'],'same-audio')
        self.assertEqual(result['execution']['mode'],'persistent')
        self.assertEqual(held,[])

    def test_alignment_dispatch_passes_retention_without_changing_deadline(self):
        module=importlib.import_module('phoneme_scoring.align_audio')
        args=['mfa.exe','align_one','source.wav']
        kwargs=dict(stdout=self.log,stderr=subprocess.STDOUT,timeout=120,check=False,creationflags=0)
        with patch.object(reuse,'run',return_value=subprocess.CompletedProcess(args,0)) as worker:
            module._execute_mfa(args,{'mfa_execution':{'reuse_process':True,'idle_sec':600}},**kwargs)
        self.assertEqual(worker.call_args.kwargs['idle_sec'],600)
        self.assertEqual(worker.call_args.kwargs['timeout'],120)
        self.assertIs(worker.call_args.kwargs['stdout'],self.log)

    def test_profile_dispatch_is_one_capture_and_preserves_cli_deadline(self):
        module=importlib.import_module('phoneme_scoring.align_audio')
        args=['mfa.exe','align_one','source.wav']
        source=Path(self.log.name).with_suffix('.pstats');source.write_bytes(b'profile-fixture')
        output=self.root/'retained-profile.pstats'
        result=subprocess.CompletedProcess(args,0);result.execution_info={'profiled':True}
        kwargs=dict(stdout=self.log,stderr=subprocess.STDOUT,timeout=120,check=False,creationflags=0)
        settings={'mfa_execution':{'reuse_process':True,'profile_next_request':True}}
        with patch.object(module,'PROFILE_PATH',output),patch.object(reuse,'run',return_value=result) as worker:
            self.assertIs(module._execute_mfa(args,settings,**kwargs),result)
            self.assertTrue(worker.call_args.kwargs['profile'])
            self.assertEqual(worker.call_args.args[0],args)
            self.assertEqual(worker.call_args.kwargs['timeout'],120)
            self.assertEqual(output.read_bytes(),b'profile-fixture')
            module._execute_mfa(args,settings,**kwargs)
            self.assertFalse(worker.call_args.kwargs['profile'])

    def test_opt_in_dispatch_falls_back_only_before_execution(self):
        module=importlib.import_module('phoneme_scoring.align_audio')
        args=['mfa.exe','align_one','source.wav']
        kwargs=dict(stdout=self.log,stderr=subprocess.STDOUT,timeout=120,check=False,creationflags=0)
        result=subprocess.CompletedProcess(args,0)
        with patch.object(module,'run_mfa',return_value=result) as cli,patch.object(reuse,'run') as worker:
            self.assertIs(module._execute_mfa(args,{},**kwargs),result)
            worker.assert_not_called()
            cli.assert_called_once_with(args,**kwargs)
        with patch.object(module,'run_mfa',return_value=result) as cli,patch.object(reuse,'run',side_effect=reuse.UnsupportedRuntime()):
            self.assertIs(module._execute_mfa(args,{'mfa_execution':{'reuse_process':True}},**kwargs),result)
            cli.assert_called_once_with(args,**kwargs)
        with patch.object(module,'run_mfa') as cli,patch.object(reuse,'run',side_effect=subprocess.TimeoutExpired(args,120)):
            with self.assertRaises(subprocess.TimeoutExpired):module._execute_mfa(args,{'mfa_execution':{'reuse_process':True}},**kwargs)
            cli.assert_not_called()


if __name__=='__main__':unittest.main()
