import contextvars, sys, os, cli

UNSET = type('UNSET',tuple(),{'__repr__':lambda _: '-', '__bool__':lambda _: False})()

def cfg(vars, pkg=None):
    ''' This is how you use a configuration variable.
    '''
    if pkg is None:
        import config
        pkg = config
# Do we need to call a target to initialize the config variables first?
    if target.v is UNSET:
        import config
        targets = {k:v for k,v in {k:getattr(config,k) for k in dir(config)}.items() if isinstance(v, Target)}
    # Figure out the default target for this environment?
        if (target_name:=env.target) is None:
            names = [name for name,t in targets.items() if t.default == cli.env]
            if len(names) != 1: raise ValueError(f"{'Multiple' if names else 'No'} default target{'s' if names else ''} set for the environment {cli.env!r}")
            target_name = names[0]
        if target_name not in targets: raise ValueError(f"Invalid target {target_name!r}.  Options: {' '.join(targets.keys())}")
    # Load the target
        targets[target_name]()
    # Environment variables override config.py
        env.load()
    # Set the target and we're done
        target(target_name)
# Return the contextvars values
    out = tuple(getattr(pkg, v).v for v in vars.split(' '))
    return out[0] if len(out) == 1 else out



class ConfigVar():
    ''' A simple wrapper around a ``contextvars.ContextVar``.

    It stores meta data like documentation and source file location for printing documentation about config variables.
    '''
    __slots__ = ('name', 'doc', 'loc', 'cvar', 'default')

    def __init__(self, name, /, default=UNSET, *, doc='', loc=1):
        if isinstance(loc, int):
            frame = sys._getframe(loc)
            loc = (frame.f_code.co_filename, frame.f_lineno)
        nd = name.split(' ',1)
        if len(nd) > 1: doc = nd[1] + (f'\n\n{doc}' if doc else '')
        self.name = nd[0]
        self.doc = doc
        self.loc = loc
        self.default = default
        self.cvar = contextvars.ContextVar(self.name, default=default)
    
    def __str__(self):
        return f"{self.name} : {self.doc} [{self.default!r}]"
    
    def __repr__(self):
        return f"ConfigVar({self.name!r}, default={self.default!r}, doc={self.doc!r}, loc={self.loc!r})"
    

    @property
    def v(self):
        return self.cvar.get()
    
    @v.setter
    def v(self, value):
        return self(value)
        
    def __call__(self, value):
        return self.cvar.set(value)



target = ConfigVar('target The target that was used to set all of the configuration variables.', loc=('__builtin__',0))



class Target():

    @classmethod
    def define(self, fn=None, *, default=None):
        ''' A decorator to mark a function as a target 
        '''
        def _wrap(fn):
            return Target(name=fn.__name__, fn=fn, default=default)
        return _wrap if fn is None else _wrap(fn)


    def __init__(self, *, name, default=None, fn):
        self.name = name
        self.fn = fn
        self.default = default

    def __call__(self):
        self.fn()



class Env():
    def __getattr__(self, key):
        return os.environ.get(f"{cli.prefix}{key}".upper())
    
    def __setattr__(self, key, value):
        os.environ[f"{cli.prefix}{key}".upper()] = value

    def load(self):
        import config
        for name in [k[len(cli.prefix):].lower() for k in os.environ if k.startswith(cli.prefix)]:
            try:
                getattr(config, name)(getattr(self, name))
            except: pass # Ignore unknown environment variables

    def __iter__(self):
        import config
        for k in dir(config):
            if not isinstance(v:=getattr(config, k), ConfigVar): continue
            yield v

env = Env()
