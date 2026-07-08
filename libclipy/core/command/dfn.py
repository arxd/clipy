import inspect, importlib
from .param import Param, Bool
from .errors import DuplicateArgumentAlias, InvalidCommandName, UnknownSubCommand, AmbiguousSubCommand

HELP = Param.from_kw('help', Bool)


class CommandDfn(type):
    ''' This serves as the type of a `Command`-derived command class object.
    '''
    def __init__(self, *_):
    # Validate the command name
        self.name = self.__func__.__name__.replace('_','-')
        if '--' in self.name: raise InvalidCommandName(dfn=self, msg="Illegal double underscore in the command name")
        if self.name[0] == '-': raise InvalidCommandName(dfn=self, msg="Illegal leading underscore in the command name")
        if self.name[-1] == '-': self.name = self.name[:-1]
    # Parse the signature
        self.var_pos = self.var_kw = None # None: does not exist;  False: private;  True: public
        self.params = {}
        self.alias = {'h':HELP, 'help':HELP} # help aliases are implicit on every command
    # Parse the function signature
        sig = inspect.signature(self.__func__)
        self.is_implicit = not sig.parameters.get('_sub_cmd')
        for i, p in enumerate(sig.parameters.values()):
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
        return hash(self.module)
    

    def __str__(self):
        return self.module
    

    def __eq__(self, other):
        return str(self) == str(other)
    
    
    def __lt__(self, other):
        return str(self) < str(other)


    def __call__(self, *args, **kwargs):
        return self.instance()(*args, **kwargs)
    

    def each(self, *args, **kwargs):
        yield from self.instance().each(*args, **kwargs)


    def instance(self):
        return super().__call__()
    

    def get_venv(self):
        from cli import env, Venv
        for venv in self.venv:
            if not venv.system or env.system in venv.system:
                return venv
        return Venv()


    def sub_commands(self, prefix=''):
        ''' Get a list of Command objects matching the `prefix`
        '''
    # yield a list of `Command` found by scanning dir(src)
        def _dir(src):
            for k in dir(src):
                if isinstance(cmd:=getattr(src,k), CommandDfn) and cmd.name.startswith(prefix): yield cmd
    # yield a list of `Command` objects inside the module loaded from `src`
        def _package_str(src):
            yield from _dir(importlib.import_module(src, package=self.module.rsplit('.',2)[0])) 
    # yield a list of matching `Command` objects from any source
        def _any(src):
            if isinstance(src, str):
                yield from _package_str(src)
            elif isinstance(src, CommandDfn):
                if src.name.startswith(prefix): yield src
            elif callable(src):
                yield from _heterogeneous(*srcs) if isinstance(srcs:=src(prefix, self), tuple) else _any(srcs)
    # Yield from a heterogeneous mixture of package-strings, Command objects, callables, and other dir()-able objects
        def _heterogeneous(*srcs):
            for src in srcs: yield from _any(src)
    # Use sub_sources given to @CLI()
        return set(_heterogeneous(*self.sub_sources))
    
    
    def get_sub_command(self, name):
        ''' Given a `name` return a sub-command `Command` or raise if unable.
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
