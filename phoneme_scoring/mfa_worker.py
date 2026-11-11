"""Private stdio worker running the unmodified installed MFA 3.3.7 CLI.

No socket/public API, model changes, skipped dependency checks or cached speech.
Native stdout/stderr go to the same private request log as the normal CLI.
"""
import atexit
import copy
from contextlib import nullcontext
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
import traceback


def main():
    started=time.monotonic()
    protocol=os.fdopen(os.dup(sys.stdout.fileno()),'w',encoding='utf-8',buffering=1)
    # Third-party imports may print outside Python's redirect_stdout.
    with open(os.devnull,'w') as quiet:
        os.dup2(quiet.fileno(),1);os.dup2(quiet.fileno(),2)
    from montreal_forced_aligner.command_line.mfa import mfa_cli
    from montreal_forced_aligner.command_line import utils
    from montreal_forced_aligner import config
    defaults={k:copy.deepcopy(v) for k,v in vars(config).items() if k.isupper() and
              isinstance(v,(str,int,float,bool,type(None),Path,list,tuple,dict))}
    original_exit,original_hook=sys.exit,sys.excepthook
    protocol.write(json.dumps({'event':'ready','startup_sec':time.monotonic()-started})+'\n')
    requests=queue.Queue()
    def receive():
        for line in sys.stdin:requests.put(line)
        requests.put(None)
    threading.Thread(target=receive,daemon=True).start()
    idle=float(sys.argv[1]) if len(sys.argv)>1 else 120
    graphs=None
    for _ in range(32):
        try:line=requests.get(timeout=idle)
        except queue.Empty:break
        if line is None:break
        request=json.loads(line)
        identity=request['id'];args=request['args']
        if not isinstance(args,list) or not args or args[0]!='align_one':
            raise ValueError('Only alignment requests are supported')
        began=time.monotonic();code=0;profiled=False;graph_info=None
        with open(request['log_path'],'a',encoding='utf-8') as log:
            os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
            for key,value in defaults.items():setattr(config,key,copy.deepcopy(value))
            old_argv=sys.argv
            sys.argv=['mfa',*args]
            utils.BEGIN=time.time();utils.BEGIN_DATE=datetime.now()
            profiler=None
            if request.get('profile') is True:
                import cProfile
                profiler=cProfile.Profile();profiler.enable()
            graph_context=nullcontext(False);before=None
            if request.get('reuse_graphs') is True:
                try:
                    from fst_resource_cache import GraphCache
                    from kalpy.fstext.lexicon import LexiconCompiler
                    if graphs is None:graphs=GraphCache()
                    before=graphs.stats()
                    graph_context=graphs.installed(LexiconCompiler)
                except (ImportError,AttributeError):pass
            elif graphs is not None:graphs.clear()
            try:
                with graph_context as installed:
                    mfa_cli.main(args=args,prog_name='mfa',standalone_mode=False)
                if before is not None:
                    after=graphs.stats()
                    graph_info=dict(enabled=installed,**{k:after[k]-before[k] for k in ['hits','misses','fallbacks']},entries=after['entries'])
            except SystemExit as exc:
                code=exc.code if isinstance(exc.code,int) else 1
            except Exception:
                code=1;traceback.print_exc(file=log)
            finally:
                hooks=getattr(sys.exit,'__self__',None)
                if isinstance(hooks,utils.ExitHooks):
                    atexit.unregister(hooks.history_save_handler)
                    hooks.exit_code=code
                    try:hooks.history_save_handler()
                    except Exception:code=1;traceback.print_exc(file=log)
                sys.exit,sys.excepthook=original_exit,original_hook
                sys.argv=old_argv
                if profiler is not None:
                    profiler.disable()
                    try:
                        profiler.dump_stats(str(Path(request['log_path']).with_suffix('.pstats')))
                        profiled=True
                    except OSError:
                        pass  # Diagnostic output must not change CLI success.
            sys.stdout.flush();sys.stderr.flush()
            # Do not leave native output attached to a previous request's log.
            with open(os.devnull,'w') as quiet:
                os.dup2(quiet.fileno(),1);os.dup2(quiet.fileno(),2)
        protocol.write(json.dumps({'id':identity,'returncode':code,'execution_sec':time.monotonic()-began,'profiled':profiled,'graph_cache':graph_info})+'\n')
        if code:break  # Do not reuse potentially poisoned library state.
    protocol.close()


if __name__=='__main__':main()
