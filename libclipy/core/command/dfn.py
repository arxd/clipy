import inspect, importlib
from .param import Param, Bool

HELP = Param.from_kw('help', Bool)


def cmd(*args, need=None, sub_required=None):
    ''' This is a decorator used on functions to turn them into `CommandDfn`.
    '''
    sub_sources = args
    def _wrap(fn):
        type = AsyncGenDfn if inspect.isasyncgenfunction(fn) else AsyncDfn if inspect.iscoroutinefunction(fn) else GenDfn if inspect.isgeneratorfunction(fn) else CommandDfn
        return type(fn.__name__, (Command,), dict(
            __func__ = fn,
            __doc__ = fn.__doc__,
            sub_sources = sub_sources,
            need = need or [],
            sub_required = bool(sub_sources) if sub_required is None else sub_required,
        ))
    if len(args) != 1 or isinstance(args[0], str): return _wrap
    sub_sources = tuple()
    return _wrap(args[0])



class CommandDfn(type):
    ''' This is a Python type that defines a command.

    It holds information about the command such as, its name, parameters (``inspect.signature``)

    Don't create CommandDfn types directly.  Instead use the `@CLI <CLI>` decorator.
    '''
    def __init__(self, *_):
    # Validate the command name
        self.name = self.__func__.__name__.replace('_','-')
        if '--' in self.name: raise InvalidCommandName(dfn=self, msg="Illegal double underscore in the command name")
        if self.name[0] == '-': raise InvalidCommandName(dfn=self, msg="Illegal leading underscore in the command name")
        if self.name[-1] == '-': self.name = self.name[:-1]
    # Parse the signature
        self.var_pos = self.var_kw = None
        self.params = {}
        self.alias = {'h':HELP, 'help':HELP} # help aliases are implicit on every command
    # Parse the function signature
        for i, p in enumerate(inspect.signature(self.__func__).parameters.values()):
            if p.kind is p.VAR_POSITIONAL: self.var_pos = (p.name[0] != '_')
            elif p.kind is p.VAR_KEYWORD: self.var_kw = (p.name[0] != '_')
            else:
            # This is a normal parameter
                p = Param.from_sig(p, None if p.kind is p.KEYWORD_ONLY else i)
                self.params[p.name] = p
            # Setup aliases for kw parameters
                if p.is_kw and p.name[0] != '_':
                    for alias in p.aliases():
                        if alias in self.alias: raise DuplicateArgumentAlias(dfn=self, alias=alias, param=p)
                        self.alias[alias] = p
                    self.alias[p.name] = p
    

    def __hash__(self):
        return hash(self.name)
    

    def __str__(self):
        return self.name
    

    def __eq__(self, other):
        return self.name == str(other)
    

    def __call__(self, *args, **kwargs):
        return self.__func__(*args, **kwargs)


    def bind(self, *args):
        return super().__call__().bind_cli(list(args))

    
    def sub_commands(self, prefix=''):
        ''' Get a list of CommandDfn objects matching the `prefix` '''
    # yield a list of `CommandDfn` found by scanning dir(src)
        def _dir(src):
            for k in dir(src):
                if isinstance(cmd:=getattr(src,k), CommandDfn) and cmd.name.startswith(prefix): yield cmd
    # yield a list of `CommandDfn` objects inside the module loaded from `src`
        def _package_str(src): 
            yield from _dir(importlib.import_module(src, package=self.__func__.__module__.rsplit('.',1)[0])) 
    # yield a list of matching `CommandDfn` objects from any source
        def _any(src):
            if isinstance(src, str):
                yield from _package_str(src)
            elif isinstance(src, CommandDfn):
                if src.name.startswith(prefix): yield src
            elif callable(src):
                yield from _hetergeneous(*srcs) if isinstance(srcs:=src(prefix), tuple) else _any(srcs)
    # Yield from a heterogeneous mixture of package-strings, CommandDfn objects, callables, and other dir()-able objects
        def _hetergeneous(*srcs):
            for src in srcs: yield from _any(src)
    # Use sub_sources given to @CLI()
        return set(_hetergeneous(*self.sub_sources))
       
    
    def sub_cmd(self, name):
        ''' Given a `name` return a sub-command `CommandDfn` or raise if unable.
        '''
        subs = self.sub_commands(name)
    # Only one match?
        if len(subs) == 1: return subs.pop()
    # No matches?
        if not subs: raise UnknownSubCommand(name=name, subs=self.sub_commands())
    # See if we have an exact match
        for s in subs:
            if s.name == name: return s
    # Too many matches
        raise AmbiguousSubCommand(name=name, subs=subs)


    def prepare(self):
        ''' Make sure we have everything we need to run this command
        '''
        for need in self.need if isinstance(self.need, (list, tuple)) else [self.need]: need(self)



class AsyncDfn(CommandDfn):
    async def __call__(self, *args, **kwargs):
        return await self.__func__(*args, **kwargs)



class AsyncGenDfn(CommandDfn):
    async def __call__(self, *args, **kwargs):
        async for x in self.__func__(*args, **kwargs): yield x



class GenDfn(CommandDfn):
    def __call__(self, *args, **kwargs):
        yield from self.__func__(*args, **kwargs)



def pip(*pip_packages):
    ''' This ensures that the pip_packages are installed
    '''
    from libclipy.setup import ensure_packages  
    return lambda *_: ensure_packages(*pip_packages)


from .command import Command
from .errors import DuplicateArgumentAlias, InvalidCommandName, UnknownSubCommand, AmbiguousSubCommand
