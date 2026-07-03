import inspect, importlib, asyncio
import multiprocessing as mp
from .param import Param, Bool

HELP = Param.from_kw('help', Bool)


def cmd(*args, need=None, sub='!'):
    ''' This is a decorator used on functions to turn them into `CommandDfn` type objects.

    Parameters:
        *args
            You may specify zero or more sub-command sources of the following type:
            
            * module : A module object (from an import statement) may be given directly.  Any top-level `CommandDfn` objects will be used a sub-commands.
            * string : A relative or absolute module path.  This module will be loaded when the sub-commands need to be queried (such as when a sub-command is called, or a list of sub-commands is needed for documentation).
            * CommandDfn : A single command can be given directly.
            * callable: When sub-commands are queried this is called with the prefix and CommandDfn to programmatically return one or more of the above sources of sub-commands.

        need | default is []
            This is a callable (or list/tuple of callables) that will be called when this command is used on the command line.
            The callables are intended to resolve any dependencies this command needs before it can be called successfully.
            All commands/sub-commands created when parsing the command line will have their needs called before the root command is called.

            Example: ``need=CLI.pip('numpy pandas')``)

        sub | default is ``!``
            This is a string specifying the name of a parameter used for command/sub-command coordination.
            If the given value ends with ``!`` or ``?`` then the command implicitly calls the sub-command, otherwise the command receives the sub-command and needs to call it explicitly.
            
            For explicit control (not ending in ``!`` or ``?``) give the name of one of the commands parameters that will receive the `Command` object (or None if no sub-command is given).

            For implicit control, give the name of the sub-command's parameter that will receive the return value from the current command.
            Immediately following the name should be a ``?`` if sub-commands are optional, or ``!`` if a sub-command is required.
            If no name is given (a naked ``!`` or ``?``) then the return value is a dictionary of kwargs that will be given to the sub-command.
            In that case, ``None`` is the same as an empty dictionary.
            
    '''
    def _wrap(fn):
        type = AsyncGenDfn if inspect.isasyncgenfunction(fn) else AsyncDfn if inspect.iscoroutinefunction(fn) else GenDfn if inspect.isgeneratorfunction(fn) else CommandDfn
        return type(fn.__name__, (Command,), dict(
            __func__ = fn,
            __doc__ = fn.__doc__,
            package = fn.__module__.rsplit('.',1)[0],
            sub_sources = args,
            need = need or [],
            sub_param_name = sub,
        ))
    return _wrap



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
    # If we are implicit then create a wrapper function to handle the sub-command execution
        self.sub_required = (self.sub_param_name.endswith('!') and self.sub_sources)
        if self.sub_param_name[-1] in '?!':
            self.__func__ = self.make_implicit_func(self.sub_param_name[:-1])
            self.sub_param_name = '_d29fdj0'
    
    
    def __hash__(self):
        return hash(self.name)
    

    def __str__(self):
        return self.name
    

    def __eq__(self, other):
        return self.name == str(other)
    

    def __call__(self, *args, **kwargs):
        self.prepare()
        return self.__func__(*args, **kwargs)


    def bind(self, *args):
        return super().__call__().bind_cli(list(args))

    
    def sub_commands(self, prefix=''):
        ''' Get a list of CommandDfn objects matching the `prefix`'''
    # yield a list of `CommandDfn` found by scanning dir(src)
        def _dir(src):
            for k in dir(src):
                if isinstance(cmd:=getattr(src,k), CommandDfn) and cmd.name.startswith(prefix): yield cmd
    # yield a list of `CommandDfn` objects inside the module loaded from `src`
        def _package_str(src):
            yield from _dir(importlib.import_module(src, package=self.package)) 
    # yield a list of matching `CommandDfn` objects from any source
        def _any(src):
            if isinstance(src, str):
                yield from _package_str(src)
            elif isinstance(src, CommandDfn):
                if src.name.startswith(prefix): yield src
            elif callable(src):
                yield from _heterogeneous(*srcs) if isinstance(srcs:=src(prefix, self), tuple) else _any(srcs)
    # Yield from a heterogeneous mixture of package-strings, CommandDfn objects, callables, and other dir()-able objects
        def _heterogeneous(*srcs):
            for src in srcs: yield from _any(src)
    # Use sub_sources given to @CLI()
        return set(_heterogeneous(*self.sub_sources))
       
    
    def get_sub_command(self, name):
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
 

    def make_implicit_func(self, param_name):
        fn = self.__func__
        def _wrap(*args, _d29fdj0=None, **kwargs):
            r = fn(*args, **kwargs)
            if _d29fdj0 is None: return r
            if param_name: r = {param_name:r}
            return _d29fdj0.call(**({} if r is None else r))
        return _wrap


    def c_call(self, *args, **kwargs):
        ''' Call this command synchronously returning a single value.

        If the underlying __func__ is async then a new event loop is needed.
        If there is already an existing event loop then a new loop cannot be created and a new sub-process is needed.

        If the underlying __func__ is a generator (or async generator) then a list will be returned with the collected values.
        '''
        return self.__func__(*args, **kwargs)


    async def c_call_async(self, *args, **kwargs):
        ''' Call this command asynchronously returning a single value.

        If the underlying __func__ is not async, then it will be run in a separate process and awaited asynchronously.

        If the underlying __func__ is a generator (or async generator) then a list will be returned with the collected values.
        '''
        raise NotImplementedError()
    

    def c_each(self, *args, **kwargs):
        ''' A generator

        If the underlying __func__ is not a generator then a single value will be yielded
        '''
        raise NotImplementedError()
        yield None
    

    async def c_each_async(self, *args, **kwargs):
        ''' An async generator

        If the underlying __func__ is not a generator then a single value will be yielded
        '''
        raise NotImplementedError()
        yield None



class AsyncDfn(CommandDfn):
    async def __call__(self, *args, **kwargs):
        return await self.__func__(*args, **kwargs)

    def make_implicit_func(self, param_name):
        fn = self.__func__
        async def _wrap(*args, _d29fdj0=None, **kwargs):
            r = await fn(*args, **kwargs)
            if _d29fdj0 is None: return r
            if param_name: r = {param_name:r}
            return await _d29fdj0.call_async(**({} if r is None else r))
        return _wrap
    

    def c_call(self, *args, **kwargs):
        if has_running_loop():
        # We are running in an existing loop so we need to use a different process to execute the function.
        # A thread is insufficient because you can't cancel a thread when ctl-c is received. 
            raise NotImplementedError()
        else:
            return run_coro(self.__func__(*args, **kwargs))
    

    async def c_call_async(self, *args, **kwargs):
        return await self.__func__(*args, **kwargs)



class AsyncGenDfn(CommandDfn):
    async def __call__(self, *args, **kwargs):
        async for x in self.__func__(*args, **kwargs): yield x

    def make_implicit_func(self, param_name):
        raise NotImplementedError()



class GenDfn(CommandDfn):
    def __call__(self, *args, **kwargs):
        yield from self.__func__(*args, **kwargs)

    def make_implicit_func(self, param_name):
        raise NotImplementedError()



def pip(*pip_packages):
    ''' This ensures that the pip_packages are installed
    '''
    from libclipy.core.setup import ensure_packages  
    return lambda *_: ensure_packages(*pip_packages)



from .command import Command
from .async_runner import run_coro, has_running_loop
from .errors import DuplicateArgumentAlias, InvalidCommandName, UnknownSubCommand, AmbiguousSubCommand
