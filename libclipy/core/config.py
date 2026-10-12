import contextvars, os, sys, inspect, importlib
from pathlib import Path

UNSET = type('UNSET',tuple(),{'__repr__':lambda _: '-', '__bool__':lambda _: False})()


def set_env_vars(prefix):
    import config
    # Set environment variables
    for k, value in os.environ.items():
        if not k.startswith(prefix): continue
        k = k[len(prefix):].lower()
        try:
            cfg_var = getattr(config, k)
            if isinstance(cfg_var, ConfigVar): cfg_var.v = value
        except AttributeError: pass


class Target():
    ''' A target is just a function that sets ConfigVars to set the execution environment for a particular workflow
    '''
    all = {}

    def __init__(self, system=''):
        self.system_fn = [s.strip() for s in (system if isinstance(system, (tuple,list)) else system.split(',')) if s.strip()] or ['']

    @classmethod
    def call(self, name, system=None):
        if name not in Target.all: return
        if system is None:
            system = globals()['system'].v
        Target.all[name].apply(system)

    def apply(self, system=''):
        for s, fn in self.system_fn:
            if not s or system == s: return fn()

    def __call__(self, fn):
        ''' The object itself is a decorator that wraps the target function
        '''
        self.name = fn.__name__
        self.system_fn = [(s,fn) for s in self.system_fn]
        if self.name in Target.all:
            Target.all[self.name].system_fn += self.system_fn
            return Target.all[self.name]
        Target.all[self.name] = self
        return self



class ConfigVar():
    ''' A simple wrapper around a ``contextvars.ContextVar``.

    It stores meta data like documentation and source file location for printing documentation about config variables.
    '''
    preserved = set()
    preserve = True
    lock = False

    @classmethod
    def set_by_name(self, src_path, value):
        module, names = src_path.split('::')
        obj = importlib.import_module(module)
        for name in names.split('.'): obj = getattr(obj, name)
        obj.v = value


    def __init__(self, name='', *, loc=1, cast=None, default=UNSET, export=None):
        frame = sys._getframe(loc)
        self.loc = (frame.f_code.co_filename, frame.f_lineno)
        self.module = frame.f_globals.get('__name__')
        name_doc = name.split(' ',1)
        self.name = name_doc[0]
        self.doc = name_doc[1] if len(name_doc) == 2 else ''
        self.cast = cast or (lambda x: x)
        self._export = export
        # python3.13 broke Path pickle across python versions
        if self._export is None: self._export = str if isinstance(cast, type) and issubclass(cast, Path) else lambda x: x
        self._default = UNSET
        if default is not UNSET: self.default = default
        if self.name: self.cvar = contextvars.ContextVar(self.name)


    @property
    def src_path(self):
        return f'{self.module}::{self.name}'


    def __hash__(self):
        return hash(self.src_path)

    def __eq__(self, other):
        return self.src_path == other.src_path

    def __str__(self):
        return self.src_path
    

    def __repr__(self):
        name_doc = f"{self.name} {self.doc}"
        return f"ConfigVar({name_doc!r}, {self.default!r}, loc={self.loc!r})"


    def __call__(self, fn):
        ''' The object itself is a decorator that uses the decorated function as its cast function

        .. code-block:: python

            @ConfigVar()
            def my_var(v=default_value):
                """ A description of my_var
                """
                return int(v)

            type(my_var) == ConfigVar
        '''
        self.cast = fn
        if fn.__doc__: self.doc = fn.__doc__
        # Figure out default value if it is not given to __init__
        sig = inspect.signature(fn)
        default = next(iter(sig.parameters.items()))[1].default
        default_value = UNSET if default is sig.empty else default
        new_default = default is not sig.empty and default_value != self.default
        if not self.name or new_default:
            if not self.name: self.name = fn.__name__
            if new_default: self.default = default_value
            self.cvar = contextvars.ContextVar(self.name)
        return self


    @property
    def v(self):
        try:
            return self.cvar.get()
        except LookupError:
            return self.default
    
    @v.setter
    def v(self, value):
        if ConfigVar.lock:
            self.default = value
        else:
            if ConfigVar.preserve: type(self).preserved.add(self)
            return self.cvar.set(self.cast(value))

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, value):
        self._default = self.cast(value)
        return self._default

    def for_child(self, value): # FIXME This is a kludge used only for out_fd, there must be a cleaner way
        self.v_child = value
        type(self).preserved.add(self)

    def export(self):
        try:
            return self._export(self.v_child)
        except AttributeError:
            return self._export(self.v)



@ConfigVar()
def target(v='local'):
    ''' The target tuple which runs the @Target functions that set variables
    '''
    return v.split('.') if isinstance(v, str) else v

verbosity = ConfigVar("verbosity Bump the verbosity positive or negative", default=0, cast=int)
system = ConfigVar('system The system environment where we are running cli.py', default='dev')
format_out = ConfigVar("format_out How should we format our command's output?", default='pretty')
out_fd = ConfigVar("out_fd The pipe fd where our output should be sent")

class LocalRoot(ConfigVar):        
    def path(self, sub_path=''):
        from cli import project_root
        return project_root / self.v / sub_path
    
    def open(self, sub_path, mode='r', *args, **kwargs):
        path = self.path(sub_path)
        if 'w' in mode or 'a' in mode or 'x' in mode:
            path.parent.mkdir(parents=True, exist_ok=True)
        return open(str(path), mode, *args, **kwargs)

local_root = LocalRoot("local_root A path to a project-specific temporary work directory", default='local', cast=Path)
