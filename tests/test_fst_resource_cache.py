"""Graph-resource lifecycle with controlled loaders; no acoustic inference."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from phoneme_scoring.fst_resource_cache import GraphCache


class Graph:
    def __init__(self,data):self.data=list(data)
    def copy(self):return Graph(self.data)


class Compiler:
    def __init__(self):self.reads=0
    def load_l_from_file(self,path):
        self.reads+=1;self._fst=Graph(Path(path).read_bytes())
    def load_l_align_from_file(self,path):
        self.reads+=1;self._align_fst=Graph(Path(path).read_bytes())


class ResourceGraphTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.source=self.root/'L.fst';self.source.write_bytes(b'original')
        self.cache=GraphCache()

    def test_identical_content_at_different_request_paths_reuses_independent_copy(self):
        first=Compiler();second=Compiler();other=self.root/'different.fst';other.write_bytes(b'original')
        with self.cache.installed(Compiler):
            first.load_l_from_file(self.source)
            first._fst.data.append(99)
            second.load_l_from_file(other)
        self.assertEqual(first.reads,1);self.assertEqual(second.reads,0)
        self.assertEqual(second._fst.data,list(b'original'))
        second._fst.data.append(42)
        self.assertEqual(self.cache.entries['_fst'][1].data,list(b'original'))
        self.assertEqual(self.cache.stats()['hits'],1)

    def test_changed_content_invalidates_and_only_two_resource_slots_exist(self):
        with self.cache.installed(Compiler):
            for value in [b'one',b'two',b'three']:
                self.source.write_bytes(value);compiler=Compiler()
                compiler.load_l_from_file(self.source);compiler.load_l_align_from_file(self.source)
                self.assertEqual(compiler.reads,2)
                self.assertEqual(compiler._fst.data,list(value))
                self.assertEqual(len(self.cache.entries),2)
        self.cache.clear();self.assertEqual(self.cache.entries,{})

    def test_hash_failure_uses_original_loader(self):
        compiler=Compiler()
        with self.cache.installed(Compiler),patch('phoneme_scoring.fst_resource_cache.fingerprint',side_effect=OSError('unreadable')):
            compiler.load_l_from_file(self.source)
        self.assertEqual(compiler.reads,1)
        self.assertEqual(compiler._fst.data,list(b'original'))
        self.assertEqual(self.cache.entries,{})

    def test_master_copy_failure_uses_original_loader(self):
        with self.cache.installed(Compiler):
            Compiler().load_l_from_file(self.source)
            master=self.cache.entries['_fst'][1]
            with patch.object(master,'copy',side_effect=RuntimeError('copy unavailable')):
                compiler=Compiler();compiler.load_l_from_file(self.source)
        self.assertEqual(compiler.reads,1)
        self.assertEqual(compiler._fst.data,list(b'original'))
        self.assertEqual(self.cache.entries,{})

    def test_original_read_failure_propagates_once(self):
        calls=[]
        def fail(instance,path):calls.append(path);raise ValueError('original failure')
        with self.assertRaisesRegex(ValueError,'original failure'):
            self.cache.load(fail,Compiler(),self.source,'_fst')
        self.assertEqual(len(calls),1)
        self.assertEqual(self.cache.entries,{})

    def test_changed_during_original_read_is_not_cached(self):
        compiler=Compiler()
        with self.cache.installed(Compiler),patch('phoneme_scoring.fst_resource_cache.fingerprint',side_effect=[b'first',b'changed']):
            compiler.load_l_from_file(self.source)
        self.assertEqual(compiler._fst.data,list(b'original'))
        self.assertEqual(self.cache.entries,{})

    def test_loaders_are_restored_when_cli_raises(self):
        original=Compiler.load_l_from_file;original_align=Compiler.load_l_align_from_file
        with self.assertRaises(ValueError),self.cache.installed(Compiler):
            raise ValueError('alignment failed')
        self.assertIs(Compiler.load_l_from_file,original)
        self.assertIs(Compiler.load_l_align_from_file,original_align)

    def test_unsupported_compiler_can_execute_without_cache(self):
        class Locked(type):
            def __setattr__(cls,name,value):raise TypeError('read only')
        class Unsupported(Compiler,metaclass=Locked):pass
        with self.cache.installed(Unsupported) as active:
            self.assertFalse(active)
            compiler=Unsupported();compiler.load_l_from_file(self.source)
        self.assertEqual(compiler.reads,1)

    def test_non_independent_copy_is_never_published(self):
        class Unsafe:
            def copy(self):return self
        def original(instance,path):instance._fst=Unsafe()
        self.cache.load(original,Compiler(),self.source,'_fst')
        self.assertEqual(self.cache.entries,{})


if __name__=='__main__':unittest.main()
