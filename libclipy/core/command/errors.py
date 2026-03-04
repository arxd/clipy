

class CommandError(Exception):
    def __init__(self, **kwargs):
        for k,v in kwargs.items(): setattr(self, k,v)



class InvalidCommandSpec(CommandError):
    pass



class BindError(CommandError):
    pass



class InvalidCommandName(InvalidCommandSpec):
    def __str__(self):
        return self.msg



class DuplicateArgumentAlias(InvalidCommandSpec):
    def __str__(self):
        if self.alias in ['help','h']: return f"The alias '{self.alias}' is reserved for help"
        return f"Parameters '{self.param}' and '{self.dfn.alias[self.alias]}' are defining the alias '{self.alias}'"



class ParseError(BindError):
    def __str__(self):
        if isinstance(self.key_arg, int):
            return f"Failed to parse the value {self.v!r} as a '{self.type}' for the {_ord(self.key_arg)} argument.  {self.msg}"
        return f"Failed to parse the value {self.v!r} as a '{self.type}' for the argument {self.key_arg}.  {self.msg}"
       


class UnknownKey(BindError):
    def __str__(self):
        options = ['-'*min(len(k),2)+k for k in self.cmd.alias if '_' not in k and k not in ['h','help']]
        msg = f"must be one of [{', '.join(options)}]" if options else "no keyword arguments accepted"
        return f"Unknown keyword argument {self.key_arg}; {msg}"
    


class MissingArgument(BindError):
    def __str__(self):
        aliases = sorted(['-'*min(len(k),2) + k for k in self.param.aliases() if '_' not in k], key=lambda x: len(x), reverse=True)
        pos = '' if self.param.idx is None else f" {_ord(self.param.idx)} positional"
        s = f"No value supplied to the{pos} parameter {self.param.name!r}"
        return f"{s}  {' '.join(aliases)}" if aliases else s
        


class NotBool(ParseError):
    def __str__(self):
        return f"Trying to use {self.key_arg} as a 'bool', but its type is '{self.param.type}'"



class ExtraArguments(BindError):
    def __str__(self):
        import shlex
        return f"Unused trailing arguments:  {shlex.join(self.extra)}"



class UnknownSubCommand(BindError):
    def __str__(self):
        return f"Unknown command {self.name!r}.  Options: {' '.join(s.name for s in self.subs)}"
    


class AmbiguousSubCommand(BindError):
    def __str__(self):
        return f"Command prefix {self.name!r} matches multiple commands: {' '.join(s.name for s in self.subs)}"
    


class HelpWanted(BindError):
    def __str__(self):
        return f"Help need {self.cmd}"



def _ord(i):
    suffix = {0:'st', 1:'nd', 2:'rd'}.get(i,'th')
    return f"{i+1}{suffix}"
