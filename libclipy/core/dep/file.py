import re, glob, hashlib
from pathlib import Path
from .dep import Resource


class File(Resource):
    ''' This is a file in the filesystem
    '''
    instances = {}

    @classmethod
    def dedup_key(self, path, **kwargs):
        return path, File

    def __init__(self, path, group=None):
        self.path = path
        self.group = group

    def __repr__(self):
        p = f"[{self.group.path}]{self.rel_path}" if self.group else self.path
        return f"{self.__class__.__name__}({p})"

    @property
    def rel_path(self):
        return self.path.relative_to(self.group.path)


    def hash(self, sha256=True):
        ''' Calculate the file's hex hash or '' if the file does not exist
        '''
        if not self.path.exists(): return ''
        
        if sha256:
            with open(self.path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        else:
            stat = self.path.stat()
            return f"{stat.st_size}_{stat.st_mtime}"



class FileGroup(File):

    def sha256(self):
        raise NotImplementedError()



        