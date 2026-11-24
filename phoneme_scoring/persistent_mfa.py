"""Opt-in reuse of an owned MFA interpreter; never cache learner results.

The caller retains the existing cross-process MFA lock for the entire call.
Supported launchers are validated against their Conda package metadata. Each
request still invokes the installed CLI with its original per-recording args.
"""
import atexit
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time
import uuid


class UnsupportedRuntime(ValueError):
    """Raised before alignment starts; caller may use the ordinary CLI."""


def install_prefix(command):
    exe = Path(command[0]) if command else None
    if exe and len(command) == 1 and exe.name.lower() == 'mfa.exe':
        return exe.resolve().parent.parent
    if exe and exe.is_absolute() and exe.name.lower() == 'python.exe' and command[1:] == ['-m', 'montreal_forced_aligner']:
        return exe.parent
    if (exe and exe.name == 'micromamba' and len(command) == 5
            and command[1:3] == ['run', '-p'] and command[4] == 'mfa'
            and Path(command[3]).is_absolute()):
        return Path(command[3])
    raise UnsupportedRuntime('Unsupported MFA launcher')


def runtime(command):
    prefix = install_prefix(command)
    metadata=list((prefix/'conda-meta').glob('montreal-forced-aligner-*.json'))
    try:
        versions = {'3.3.7', '3.4.2'} if command[1:] == ['-m', 'montreal_forced_aligner'] else {'3.3.7'}
        if len(metadata)!=1 or json.loads(metadata[0].read_text(encoding='utf-8')).get('version') not in versions:
            raise UnsupportedRuntime('Unsupported MFA package version')
        python = prefix / ('bin/python' if len(command) == 5 else 'python.exe')
        if not python.is_file():raise UnsupportedRuntime('MFA Python is unavailable')
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        raise UnsupportedRuntime('MFA runtime could not be verified') from exc
    return python,hashlib.sha256(metadata[0].read_bytes()).hexdigest()


class Client:
    def __init__(self,python,env,*,worker_script=None,idle_sec=120,launcher=()):
        script=Path(worker_script) if worker_script else Path(__file__).with_name('mfa_worker.py')
        self.process=subprocess.Popen([*launcher,str(python),'-B','-u',str(script),str(idle_sec)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            text=True,encoding='utf-8',bufsize=1,env=env,start_new_session=os.name=='posix',
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.responses=queue.Queue()
        self.calls=0
        self.startup_sec=None
        self.lock=threading.Lock()
        self.reader=threading.Thread(target=self._read,daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                try:self.responses.put(json.loads(line))
                except ValueError:
                    self.responses.put({'protocol_error':True});return
        finally:self.responses.put(None)

    def run(self,args,log_path,timeout,*,profile=False,reuse_graphs=False):
        if not self.lock.acquire(blocking=False):raise RuntimeError('Reusable MFA is busy')
        began=time.monotonic();identity=uuid.uuid4().hex
        try:
            request={'id':identity,'args':args[1:],'log_path':str(Path(log_path).resolve())}
            if profile is True:request['profile']=True
            if reuse_graphs is True:request['reuse_graphs']=True
            self.process.stdin.write(json.dumps(request)+'\n');self.process.stdin.flush()
            while True:
                remaining=timeout-(time.monotonic()-began)
                if remaining<=0:raise subprocess.TimeoutExpired(args,timeout)
                try:response=self.responses.get(timeout=remaining)
                except queue.Empty:raise subprocess.TimeoutExpired(args,timeout) from None
                if response is None:raise RuntimeError('Reusable MFA stopped unexpectedly')
                if not isinstance(response,dict):raise RuntimeError('Invalid MFA response')
                if response.get('event')=='ready':
                    self.startup_sec=response['startup_sec'];continue
                if response.get('id')!=identity or type(response.get('returncode')) is not int:
                    raise RuntimeError('MFA response identity mismatch')
                self.calls+=1
                result=subprocess.CompletedProcess(args,response['returncode'])
                result.execution_info=dict(mode='persistent',pid=self.process.pid,reused=self.calls>1,
                    startup_sec=self.startup_sec if self.calls==1 else 0,
                    request_execution_sec=response.get('execution_sec'))
                if response.get('profiled') is True:result.execution_info['profiled']=True
                if isinstance(response.get('graph_cache'),dict):result.execution_info['graph_cache']=response['graph_cache']
                if result.returncode:self.close()
                return result
        except BaseException:
            self.close();raise
        finally:self.lock.release()

    def close(self):
        process=self.process
        if process.poll() is None:
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=False,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if process.poll() is None:
                    process.kill()
            else:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            process.wait(timeout=5)
        if process.stdin and not process.stdin.closed:process.stdin.close()
        if self.reader is not threading.current_thread():self.reader.join(timeout=2)
        if process.stdout and not process.stdout.closed:process.stdout.close()


_clients={}
_guard=threading.Lock()


def run(args,*,stdout,timeout,env=None,idle_sec=120,profile=False,reuse_graphs=False):
    """Execute under caller's lock; on actual failure do not silently retry CLI."""
    if type(idle_sec) is not int or not 30 <= idle_sec <= 600:
        raise ValueError('MFA idle retention must be an integer from 30 to 600 seconds')
    try:
        operation = args.index('align_one')
    except ValueError as exc:
        raise UnsupportedRuntime('Expected an align_one request') from exc
    command = args[:operation]
    python,version=runtime(command)
    launcher = command[:-1] if len(command) == 5 else []
    effective=os.environ.copy() if env is None else env
    script=Path(__file__).with_name('mfa_worker.py')
    cache_script=Path(__file__).with_name('fst_resource_cache.py')
    cache_version=hashlib.sha256(cache_script.read_bytes()).hexdigest() if cache_script.is_file() else None
    identity=json.dumps([str(python),launcher,version,effective,hashlib.sha256(script.read_bytes()).hexdigest(),cache_version,idle_sec],sort_keys=True)
    key=hashlib.sha256(identity.encode()).hexdigest()
    with _guard:
        client=_clients.get(key)
        if client is None or client.process.poll() is not None:
            if client:client.close()
            # Keep at most one owned interpreter per analysis process.
            for other in _clients.values():other.close()
            _clients.clear()
            client=Client(python,effective,idle_sec=idle_sec,**({'launcher':launcher} if launcher else {}));_clients[key]=client
    result = client.run([command[-1], *args[operation:]],stdout.name,timeout,profile=profile,reuse_graphs=reuse_graphs)
    result.args = args
    return result


def close_all():
    with _guard:
        for client in _clients.values():client.close()
        _clients.clear()


atexit.register(close_all)
