import contextvars, sys, os, inspect, cli

UNSET = type('UNSET',tuple(),{'__repr__':lambda _: '-', '__bool__':lambda _: False})()


def initialize_config_vars():
    import config
    # First load the env variables so the target functions can use them
    clipy_env.load()
    # Figure out the targets
    targets = {k:v for k,v in {k:getattr(config,k) for k in dir(config)}.items() if isinstance(v, Target)}
# Figure out the default target for this environment?
    if (target_name := clipy_env.target) is None:
        names = [name for name,t in targets.items() if t.default == env.v]
        if len(names) != 1: raise ValueError(f"{'Multiple' if names else 'No'} default target{'s' if names else ''} set for the environment {env.v!r}")
        target_name = names[0]
    if target_name not in targets: raise ValueError(f"Invalid target {target_name!r}.  Options: {' '.join(targets.keys())}")
# Load the target
    targets[target_name]()
# Environment variables overwrite config.py
    clipy_env.load()



def config_var(fn=None, **kwargs):
    def _wrap(fn):
        sig = inspect.signature(fn)
        frame = sys._getframe(kwargs.get('loc', 1))
        default = next(iter(sig.parameters.items()))[1].default
        return ConfigVar(
            name    = kwargs.get('name',fn.__name__),
            default = UNSET if default is sig.empty else fn(default),
            doc     = fn.__doc__,
            type    = str if (v:=sig.return_annotation) is sig.empty else v,
            cast    = fn,
            loc     = (frame.f_code.co_filename, frame.f_lineno),
        )
    return _wrap if fn is None else _wrap(fn)



class ConfigVar():
    ''' A simple wrapper around a ``contextvars.ContextVar``.

    It stores meta data like documentation and source file location for printing documentation about config variables.
    '''

    def __init__(self, **kwargs):
        for k,v in kwargs.items(): setattr(self, k, v)
        self.cvar = contextvars.ContextVar(self.name, default=self.default)
    
    def __str__(self):
        return f"{self.name} : {self.doc} [{self.default!r}]"
    
    def __repr__(self):
        return f"ConfigVar({self.name!r}, default={self.default!r}, doc={self.doc!r}, loc={self.loc!r})"

    @property
    def v(self):
        return self.cvar.get()
    
    @v.setter
    def v(self, value):
        return self.cvar.set(self.cast(value))



@config_var
def env(v='dev'):
    ''' The environment in which we are running
    '''
    return str(v)



@config_var
def target(v) -> str:
    ''' The target that was used to set all of the configuration variables.
    '''
    return str(v)



@config_var
def verbosity(v=0) -> int:
    ''' This is an integer verbosity level.  Positive means more verbose, negative is less verbose, and zero is neutral.
    Any output's verbosity will be adjusted by this amount automatically before getting streamed out.
    '''
    return int(v)



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
        os.environ[f"{cli.prefix}{key}".upper()] = str(value)

    def load(self):
        import config
        for env_name in [k for k in os.environ if k.startswith(cli.prefix)]:
            name = env_name[len(cli.prefix):].lower()
            cfg_var = {'verbosity':verbosity, 'target':target, 'env':env}.get(name)
            if cfg_var is None:
                try:
                    cfg_var = getattr(config, name)
                except:
                    print(f"Ignoring unknown env variable: {env_name}")
                    continue
            cfg_var.v = os.environ[env_name]


    def __iter__(self):
        import config
        for k in dir(config):
            if not isinstance(v:=getattr(config, k), ConfigVar): continue
            yield v

clipy_env = Env()
