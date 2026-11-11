"""Bounded copies of compiled lexicon resources inside one serial MFA worker.

No learner input, transcript, alignment or result is cached. The installed
loader remains the fallback. Masters are never given to an alignment caller.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path


def fingerprint(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
    return digest.digest()


class GraphCache:
    def __init__(self):
        self.entries={}
        self.hits=self.misses=self.fallbacks=0

    def clear(self):self.entries.clear()

    def stats(self):
        return dict(hits=self.hits,misses=self.misses,fallbacks=self.fallbacks,entries=len(self.entries))

    def load(self,original,instance,path,attribute):
        try:key=fingerprint(path)
        except Exception:
            self.fallbacks+=1
            return original(instance,path)
        entry=self.entries.get(attribute)
        if entry and entry[0]==key:
            try:
                graph=entry[1].copy()
                if graph is entry[1]:raise ValueError('Graph copy must be independent')
                setattr(instance,attribute,graph)
                self.hits+=1
                return None
            except Exception:
                self.entries.pop(attribute,None);self.fallbacks+=1
                return original(instance,path)
        self.entries.pop(attribute,None)
        self.misses+=1
        # Original read failures propagate exactly once, as without the cache.
        result=original(instance,path)
        try:
            graph=getattr(instance,attribute)
            master=graph.copy()
            if master is graph or fingerprint(path)!=key:
                raise ValueError('Graph changed while reading')
            self.entries[attribute]=(key,master)
        except Exception:
            self.entries.pop(attribute,None);self.fallbacks+=1
        return result

    @contextmanager
    def installed(self,compiler):
        try:
            original=compiler.load_l_from_file
            original_align=compiler.load_l_align_from_file
            if not callable(original) or not callable(original_align):raise AttributeError()
        except AttributeError:
            yield False
            return
        def load(instance,l_fst_path):
            return self.load(original,instance,l_fst_path,'_fst')
        def load_align(instance,l_fst_path):
            return self.load(original_align,instance,l_fst_path,'_align_fst')
        changed=[]
        try:
            compiler.load_l_from_file=load;changed.append(('load_l_from_file',original))
            compiler.load_l_align_from_file=load_align;changed.append(('load_l_align_from_file',original_align))
        except Exception:
            # These are Python methods in the inspected MFA/kalpy runtime.
            # If a different class cannot be patched, leave its loaders intact.
            for name,method in reversed(changed):setattr(compiler,name,method)
            yield False
            return
        try:yield True
        finally:
            for name,method in reversed(changed):setattr(compiler,name,method)
