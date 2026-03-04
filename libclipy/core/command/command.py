
class Command():
    ''' A Command is an object of type `CommandDfn`.

    You can bind arguments to it and then run it.
    '''
    
    def __init__(self):
    # These are the arguments (just the values) to the commands
        self.args = [Param.unset for p in self.params.values() if p.idx is not None]
        self.kwargs = {}
        self.sub = None
        self.vargs = []


    def __repr__(self):
        args = [f"{v!r}" for v in self.args + self.vargs]
        args += [f"{str(self.alias.get(k,k))}={v!r}" for k,v in self.kwargs.items()]
        s = f"{self.name}({', '.join(args)})"
        return s if self.sub is None else f"{s} -> {self.sub!r}"


    def __call__(self, *args, **kwargs):
        args, kwargs = self.args_kwargs(*args, **kwargs)
        if args and args[0] is self.sub: 
            return type(self).__func__(*args, **kwargs)
        else:
            r = type(self).__func__(*args, **kwargs)
            if self.sub is None: return r
            if r is None: r = ([], {})
            if len(r) == 1: r = ([], r[0]) if isinstance(r, dict) else (r[0], {})
            return self.sub(*r[0], **r[1])


    def bind_cli(self, args):
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
            self.bind_sub(args)
        return self
    

    def bind_sub(self, args):
    # If we don't have sub-command arguments make sure that we done require a sub-command
        if not args:
            if type(self).sub_required: raise HelpWanted(cmd=self)
            return
    # Attempt to find the sub
        try:
            sub = type(self).sub_cmd(args[0])
        except (UnknownSubCommand, AmbiguousSubCommand) as e:
            if not e.subs: raise ExtraArguments(cmd=self, extra=args)
            raise e
    # We found a sub CommandDfn
        sub.prepare()
        self.sub = sub.bind(*args[1:])


    def args_kwargs(self, *default_args, **default_kwargs):
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
                    if (v:=p.default) is Param.unset: raise MissingArgument(param=p)
                kwargs[p.name] = v
            else:
         # Positional or keyword
                # Inject the sub-command as the first arg?
                if not p.is_kw and p.name.startswith('_') and p.idx == 0:
                    args.append(self.sub)
                    continue
            # First pop off a keyword if possible.  This will not be a keyword from the command line, so it is a good starting place
                v = default_kwargs.pop(p.name) if p.is_kw and p.name in default_kwargs else Param.unset
            # Overwrite with the command-line argument
                if self.args[p.idx] is not Param.unset: v = self.args[p.idx]
            # Take from default_args if unset
                if v is Param.unset and p.idx < len(default_args): v = default_args[p.idx]
                if v is Param.unset and (v:=p.default) is Param.unset: raise MissingArgument(param=p)
                args.append(v)
    # args and kwargs fills the needed parameters.  What about var args?
        if self.var_pos is not None: args.extend(self.vargs or default_args[len(args):])
        elif default_args[len(args):]: raise TypeError(f"Only {len(args)} positional arguments allowed, but {len(default_args)} were given")
        if self.var_kw is None and default_kwargs: raise TypeError(f"Got unexpected keyword arguments: {', '.join(repr(x) for x in default_kwargs)}")
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



from .param import Param, Bool, Str
from .dfn import HELP
from .errors import UnknownKey, NotBool, MissingArgument, ExtraArguments, UnknownSubCommand, AmbiguousSubCommand, HelpWanted
