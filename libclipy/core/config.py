import contextvars, os, sys, inspect

UNSET = type('UNSET',tuple(),{'__repr__':lambda _: '-', '__bool__':lambda _: False})()


def initialize_config(env):
    import cli
# Collect mappings from environment variables to ConfigVars
    env_cfg_vars = []
    for k,v in cli.env.items():
        try:
            cfg_var = getattr(cli, k)
            if isinstance(cfg_var, ConfigVar):
                env_cfg_vars.append((cfg_var, v))
        except:
            continue
# Set private env variables
    for k,v in (env or {}).items(): cli.env[k] = v
# Set config from the env so the target has access, then set the target, finally make sure the environment overrides the target.
    for cfg_var, v in env_cfg_vars: cfg_var.v = v
    getattr(cli, cli.env.target).apply()
    for cfg_var, v in env_cfg_vars: cfg_var.v = v




class ConfigVar():
    ''' A simple wrapper around a ``contextvars.ContextVar``.

    It stores meta data like documentation and source file location for printing documentation about config variables.
    '''

    def __init__(self, name='', *, loc=1, cast=None, **kwargs):
        frame = sys._getframe(loc)
        self.loc = (frame.f_code.co_filename, frame.f_lineno)
        name_doc = name.split(' ',1)
        self.name = name_doc[0]
        self.doc = name_doc[1] if len(name_doc) == 2 else ''
        self.cast = cast or (lambda x: x)
        if 'default' in kwargs:
            self.default = UNSET if kwargs['default'] is UNSET else self.cast(kwargs['default'])
        if self.name and hasattr(self, 'default'):
            self.cvar = contextvars.ContextVar(self.name, default=self.default)
        

    def __str__(self):
        return f"{self.name} : {self.doc} [{self.default!r}]"
    

    def __repr__(self):
        name_doc = f"{self.name} {self.doc}"
        return f"ConfigVar({name_doc!r}, {self.default!r}, loc={self.loc!r})"


    def __call__(self, fn):
        ''' The object itself is a decorator that uses the decorated function as its cast function

        .. code-block:: python

            @config_var
            def my_var(v=default_value):
                """ A description of my_var
                """
                return int(v)

            type(my_var) == ConfigVar
        '''
        self.cast = fn
        if not self.name: self.name = fn.__name__
        self.doc += fn.__doc__ or ''
        # Figure out default value if it is not given to __init__
        if not hasattr(self, 'default'):
            sig = inspect.signature(fn)
            default = next(iter(sig.parameters.items()))[1].default
            self.default = UNSET if default is sig.empty else self.cast(default)
        # Create cvar if it hasn't been created yet
        if not hasattr(self, 'cvar'):
            self.cvar = contextvars.ContextVar(self.name, default=self.default)
        return self


    @property
    def v(self):
        return self.cvar.get()
    
    @v.setter
    def v(self, value):
        return self.cvar.set(self.cast(value))



class Target():
    ''' A target is just a function that sets ConfigVars to set the execution environment for a particular workflow
    '''

    def __call__(self, fn):
        ''' The object itself is a decorator that wraps the target function
        '''
        self.name = fn.__name__
        self.apply = fn
        return self



class Env():
    ''' A simple way of interacting with os.environ for only certain prefixed variables
    '''
    def __init__(self, prefix, _private_variables=None, **kwargs):
        super().__setattr__('_Env__prefix', prefix)
        super().__setattr__('_Env__defaults', kwargs)
        super().__setattr__('_Env__private_variables', _private_variables or {})


    def __getattr__(self, key):
        return self[key]
    
    
    def __getitem__(self, key):
        default = self.__defaults.get(key)
        if key.startswith('_'): return self.__private_variables.get(key, default)
        cast = str if default is None else type(default)
        v = os.environ.get(f"{self.__prefix}{key}".upper(), default)
        return None if v is None else cast(v)
    

    def __setattr__(self, key, value):
        self[key] = value


    def __setitem__(self, key, value):
        if key.startswith('_'):
            self.__private_variables[key] = value
        else:
            os.environ[f"{self.__prefix}{key}".upper()] = str(value)


    def items(self):
        for name in os.environ:
            if not name.startswith(self.__prefix): continue
            key = name[len(self.__prefix):].lower()
            yield key, os.environ[name]
