import inspect, importlib, os, subprocess, pickle, atexit, sys
from collections import namedtuple
from .dfn import CommandDfn, HELP
from .param import Param, Bool, Str
from .errors import UnknownKey, NotBool, MissingArgument, ExtraArguments, UnknownSubCommand, AmbiguousSubCommand, HelpWanted, SubRequired
from libclipy.tools.run import Exec

class Command():
    ''' This represents a possible entry point of the project.

    A clipy-based project is a tree of `Command` commands.
    These commands are the new entry points of the project, as opposed to script files running as "__main__".

    Commands can have individual (even conflicting) virtual environment requirements (python_version and requirements).

    A command may have one or more children and be called with one of them as a sub-command.

    While not listed as a metaclass, subclasses of `Command` will have a type of `CommandDfn`.
    '''

    @staticmethod
    def _unpickle(path):
        module, name = path.rsplit('.',1)
        return getattr(importlib.import_module(module), name).instance()


    def __reduce__(self):
        return (Command._unpickle, (self.module,), self.__dict__)


    def __new__(self, *args, sub_required=True):
        ''' You can't create instances of Command, only its subclasses.
        
        Instead, calling ``Command(...)`` serves as a decorator to a function that returns a subclass of Command.
        
        Parameters:
            *args: You may specify zero or more sources of sub-commands of the following type:
                
                * module : A module object (from an import statement) may be given directly.  Any top-level `CommandDfn` objects will be used as sub-commands.
                * string : A relative or absolute module path.  This module will be loaded when the sub-commands need to be queried (such as when a sub-command is called, or a list of sub-commands is needed for documentation).
                * CommandDfn : A single command can be given directly.
                * callable : When sub-commands are queried this is called with the prefix and CommandDfn to programmatically return one or more of the above sources of sub-commands.
            sub_required (bool, optional): Does this command require a sub command? 
        '''
        if self is not Command: return super().__new__(self)
        def _wrap(fn):
            async_gen = inspect.isasyncgenfunction(fn)
            return CommandDfn(fn.__name__, (Command,), dict(
                __func__ = fn,
                __doc__ = fn.__doc__,
                module = f'{fn.__module__}.{fn.__name__}',
                sub_sources = args,
                sub_required = args and sub_required,
                is_async = async_gen or inspect.iscoroutinefunction(fn),
                is_generator = async_gen or inspect.isgeneratorfunction(fn),
                venv = []
            ))
        return _wrap

    
    def __init__(self):
    # These are the bound arguments (just the values) to this command
        self.args = [Param.unset for p in self.params.values() if p.idx is not None]
        self.kwargs = {}
    # If we have a sub-command
        self.sub = None
    # The string arguments if our CommandDfn defined *args
        self.vargs = []


    def __repr__(self):
        args = [f"{v!r}" for v in self.args + self.vargs]
        args += [f"{str(self.alias.get(k,k))}={v!r}" for k,v in self.kwargs.items()]
        s = f"{self.name}({', '.join(args)})"
        return s if self.sub is None else f"{s} -> {self.sub!r}"


    def __call__(self, *args, **kwargs):
        ''' Call the command synchronously
        '''
        r = list(self.each(*args, **kwargs))
        if len(r) == 0: return Param.unset
        return r[0] if len(r) == 1 else tuple(r)
    

    async def wait(self, *args, **kwargs):
        ''' Call the command asynchronously
        '''
        r = [x async for x in self.each_async(*args, **kwargs)]
        if len(r) == 0: return Param.unset
        return r[0] if len(r) == 1 else tuple(r)


    def each(self, *args, **kwargs):
        ''' A generator that yields each output of the command
        '''
        venv = type(self).get_venv()
        data_fd = os.pipe()
        out_fd = os.pipe()
        os.set_inheritable(out_fd[0], True)
        os.write(data_fd[1], pickle.dumps({'args':args, 'kwargs':kwargs, 'cmd':self}, protocol=5))
        os.close(data_fd[1])
        env = os.environ.copy()
        env['_CLIPY_FD'] = str(out_fd[1])
        proc = subprocess.Popen([venv.venv_path('bin/python'), '-I','libclipy/core/entry_point.py', str(data_fd[0])], pass_fds=(data_fd[0], out_fd[1]) if sys.platform != "win32" else None, env=env)
        def _cleanup():
            proc.kill()
            proc.wait()
        atexit.register(_cleanup)
        os.close(out_fd[1])
        try:
            with open(out_fd[0], 'rb', closefd=True) as pipe_in:
                while True:
                    try:
                        item = pickle.load(pipe_in)
                        if isinstance(item, Exception):
                            print(item.traceback_text)
                            raise item
                        yield item
                    except EOFError:
                        break
            proc.wait()
            if proc.returncode != 0: raise ValueError(f"Subprocess had a non-zero exit: {proc.returncode}")
        finally:
            atexit.unregister(_cleanup)
            _cleanup()


    async def each_async(self, *args, **kwargs):
        ''' An async generator that yields each output of the command as they arrive
        '''
        raise NotImplementedError()


    def exec(self, *args, **kwargs):
        ''' Replace the current process with this command running in its venv.
        '''
        return Exec(venv=type(self).get_venv(), data={'cmd':self, 'args':args, 'kwargs':kwargs})


    def bind(self, *args):
        ''' `args` is a list of string arguments that came from the command line.
        They are parsed and matched to the command's parameters.
        '''
        args = list(args)
    # First parse positional arguments
        for p in self.params.values():
            if not args or p.idx is None: break
            if p.name[0] == '_': continue # Ignore _underscore_names
            self.args[p.idx], kw = p.type(p.idx, args, Param.unset)
            if kw: break # We found a key, so move to parsing keyword arguments
    # Next, parse keyword arguments
        for args, key_arg, key, is_flag in _each_key(args):
        # Is this param in the signature, or new?
            if (p:=self.alias.get(key)) is None:
                if not self.var_kw: raise UnknownKey(cmd=self, key_arg=key_arg)
            # We accept **kwargs, so create a new Param for it
                p = Param.from_kw(key.replace('-','_'), Bool if is_flag else Str)
            if p is HELP: raise HelpWanted(cmd=self)
            if is_flag and not isinstance(p.type, Bool): raise NotBool(cmd=self, key_arg=key_arg, param=p)
        # Pull v from the positional as the initial value if possible
            v = self.kwargs.get(p.name, Param.unset if p.idx is None else self.args[p.idx])
            v, kw = p.type(key_arg or p.idx, [] if is_flag else args, v)
            if kw: raise MissingArgument(param=p)
        # if possible, put v into the positional arguments, otherwise put it in kwargs
            if p.idx is None:
                self.kwargs[p.name] = v
            else:
                self.args[p.idx] = v 
    # Finally add the rest to var_pos, or the next command
        if self.var_pos:
            self.vargs = args
        else:
            self._bind_sub(args)
        return self
    

    def _bind_sub(self, args):
        ''' We (might) have extra arguments from `bind()` so treat them as a sub-command.
        '''
    # If we don't have sub-command arguments make sure that we don't require a sub-command
        if not args:
            if type(self).sub_required: raise SubRequired(cmd=self)
            return
    # Attempt to find the sub
        try:
            sub = type(self).get_sub_command(args[0] or '<blank>')
        except (UnknownSubCommand, AmbiguousSubCommand) as e:
            if not e.subs: raise ExtraArguments(cmd=self, extra=args)
            raise e
    # We found a sub CommandDfn
        self.sub = sub.instance().bind(*args[1:])


    def args_kwargs(self, *default_args, **default_kwargs):
        ''' Figure out final args/kwargs for calling the commands function (__func__).
        Any arguments previously bound with bind() will take precedent over the default args given to this method.
        '''
    # Validate the default arguments
        if 'h' in default_kwargs or 'help' in default_kwargs: raise ValueError(f"'help' and 'h' are reserved keywords")
        default_kwargs.update({k:v for k,v in self.kwargs.items() if v is not Param.unset})
        args = []
        kwargs = {}
    # Find a value for each parameter
        for p in self.params.values():
            if p.idx is None:
        # Keyword only
                try:
                    v = default_kwargs.pop(p.name)
                    if v is Param.unset: raise KeyError()
                except KeyError:
                    if (v:=p.default) is Param.unset: raise MissingArgument(param=p) from None
                kwargs[p.name] = v
            else:
         # Positional or keyword
            # First pop off a keyword if possible.  This will not be a keyword from the command line, so it is a good starting place
                v = default_kwargs.pop(p.name) if p.is_kw and p.name in default_kwargs else Param.unset
            # Overwrite with the command-line argument
                if self.args[p.idx] is not Param.unset: v = self.args[p.idx]
            # Take from default_args if unset
                if v is Param.unset and p.idx < len(default_args): v = default_args[p.idx]
                if v is Param.unset and (v:=p.default) is Param.unset: raise MissingArgument(param=p)
                args.append(v)
    # handle any remaining default_args or default_kwargs
        if self.var_pos is None and default_args[len(args):]:
            raise TypeError(f"Only {len(args)} positional arguments allowed, but {len(default_args)} were given")
        if self.var_kw is None and default_kwargs:
            raise TypeError(f"Got unexpected keyword arguments: {', '.join(repr(x) for x in default_kwargs)}")  
        # any command-line provided self.vargs trump any extra default_args regardless of length
        args.extend(self.vargs or default_args[len(args):])
        # Add only new keys from default_kwargs
        for k in default_kwargs.keys() - kwargs.keys(): kwargs[k] = default_kwargs[k]
        return (args, kwargs)



def _each_key(args):
    while args:
        arg = args.pop(0)
    # Did we get to the next command?
        if arg[0] != '-':
            args.insert(0, arg) # put it back
            return
        if arg == '--': return
    # Parse the keyword name
        arg = arg.split('=', 1)
        if len(arg) == 2: args.insert(0, '\\'+arg[1])
        arg = arg[0]
        dashes = 1 + int(arg[1] == '-')
        key_val = arg[dashes:].split('=',1)
        key = key_val[0].replace('_','-')
        keys = [key] if dashes==2 else list(key)
        for i, key in enumerate(keys):
            yield args, f"`{arg}`" if len(keys) == 1 else f"`{key}` from `{arg}`", key, i < len(keys)-1
