from pathlib import Path
from .dep import Resource, Resolver, Condition
from .file import File, FileGroup
from libclipy.tools.cc import CC


class CompilerError(Exception):
    def __init__(self, errors):
        self.errors = errors


class Compile(Resolver):
    ''' Compile a CSrc to an Obj
    '''
    def __init__(self, src, obj, cc=None, flags=None):
        self.deps = {'cc':cc or SysToolRsc(CC), 'src':src, 'obj':obj, 'flags':flags}

    def execute(self):
        deps, errs = self.cc().compile(src=self.src, obj=self.obj)
        if errs: raise CompilerError(errs)


class UpToDate(Condition):
    ''' Given a bunch of resources and conditions this keeps track if anything has changed since this
    '''
    def __init__(self, out):
        super().__init__()
        self.deps = {'out':out}

    #def poll(self):




class CSrc(File):
    ''' A C source code file
    '''
    def __init__(self, *args, **kwargs):
        print(f"CSrc{args}{kwargs}")

class Obj(File):
    ''' A compiled object file
    '''
    def __init__(self, *args, **kwargs):
        print(f"Obj{args}{kwargs}")

class Lib(File):
    ''' A compiled static library file
    '''

class DynLib(File):
    ''' A compiled dynamic library file
    '''

class Exe(File):
    ''' An executable file
    '''

    @classmethod
    def build(self, out, src=None, cc=None, cc_args=None):
        build = Dir('local/build')
        Exe(Path(out).resolve())
        from libclipy.tools.cc import CC
        cc = SysToolRsc(cc or CC, *(cc_args or tuple()))
        objs = []
        for path in map(Path, src or []):
            if path.suffix == '.c':
                csrc = CSrc(path)
                CSrc.compile(path)

                objs.append(build.file(path.with_suffix('.o'), Obj))
            elif path.suffix == '.o':
                objs.append(build.file(path, Obj))
            else:
                raise ValueError(f"Unknown source file {path} for {out}")
        
        

