import types

def _is_kw(s):
    if not s or s[0] != '-': return False
    return not s.split('=',1)[0].translate(str.maketrans('','','-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'))



class Param():
    ''' A parameter signature (name, type, default_value, positional/keyword) of a `Command`.
    '''
    unset = type('unset',tuple(),{'__repr__':lambda _: '-', '__bool__':lambda _: False})()

    __slots__ = ('name', 'type', 'idx', 'is_kw', 'default')


    @classmethod
    def from_kw(self, name, type):
        return self(name=name, idx=None, is_kw=True, type=type)


    @classmethod
    def from_sig(self, sig, idx):
        return self(
            name = sig.name,
            idx = idx,
            is_kw = sig.kind is not sig.POSITIONAL_ONLY,
            type = ParamType.from_sig(sig),
            default = Param.unset if sig.default is sig.empty else sig.default,
        )
    

    def __init__(self, *, type, **kwargs):
        for k,v in kwargs.items(): setattr(self, k, v)
        self.type = type()


    def aliases(self):
        if not self.is_kw or self.name.startswith('_'): return
        for alias in self.name.rsplit('__'):
            if not alias: continue
            if alias[-1] == '_': alias = alias[:-1]
            yield alias
            if '_' in alias: yield alias.replace('_','-')


    def __str__(self):
        return self.name



class ParamType():
    ''' The type of the parameter is derived from its annotation or default value
    '''
    @classmethod
    def from_sig(self, sig):
        k = sig.annotation if sig.annotation is not sig.empty else sig.default if sig.default is not sig.empty else str
        def _find_type(o, sub=False):
            if isinstance(o, type) and issubclass(o, ParamType): return o
            if o is bool or isinstance(o, bool): return Bool
            if o is int or isinstance(o, int): return Int
            if o is float or isinstance(o, float): return Float
            if o is list: return composite(List, Str)
            if isinstance(o, list): return composite(List, *[_find_type(s, True) for s in o])
            if o is tuple: return composite(Tuple, Str)
            if isinstance(o, tuple): return composite(Tuple, *[_find_type(s, True) for s in o])
            if isinstance(o, types.GenericAlias):
                subs = [_find_type(s, True) for s in o.__args__]
                if o.__origin__ is tuple: return composite(Tuple, *subs)
                return composite(List, *subs)
            return Str
        return _find_type(k)


    def __str__(self):
        return type(self).name


    def __call__(self, *args):
        self.key_arg, self.args, self.v = args
        return self.parse()
    

    def take(self):
    # Grab the first argument
        self.arg = self.args.pop(0)
    # If it is a `-` then we are done with an `unset` value
        if self.arg == '-': return Param.unset, False
    # Always remove a leading backslash if we can
        sval = self.arg[1:] if self.arg.startswith('\\') else self.arg
    # sval may be a keyword but maybe we still want to parse it as a value (negative numbers)
        return sval, _is_kw(self.arg)

    
    def parse(self):
        if not self.args: return Param.unset, True
        sval, kw = self.take()
        if sval is Param.unset: return Param.unset, False
        try:
            return self.simple_parse(sval, kw), False
        except Exception as e:
            if not kw: raise ParseError(msg=str(e), key_arg=self.key_arg, type=self, v=self.arg)
        # We failed to parse what looks like a keyword, put it back and try it as a keyword
            self.args.insert(0, self.arg)
            return Param.unset, True



class Composite(ParamType):
    def __init__(self, *subs):
        self.subs = subs or [Str()]

    def __str__(self):
        return f"{type(self).name}[{','.join(type(s).name for s in self.subs)}]"



class List(Composite):

    name = 'list'

    def parse(self):
        v = []
        i = 0
        while True:
            x, kw = self.subs[0](i, self.args, Param.unset)
            if x is Param.unset or kw: break
            v.append(x)
            i += 1
        return ((self.v or []) + v) or Param.unset, kw if isinstance(self.key_arg, int) else not v



def param_type(name):
    def _wrap(fn):
        return type(fn.__name__, (ParamType,), {'simple_parse':fn, 'name':name})
    if isinstance(name, str): return _wrap
    fn, name = name, None
    return _wrap(fn)



@param_type('int')
def Int(self, sval, _):
    def _parse(v):
        if v.lower().startswith('0x'): return int(v, 16)
        if v.lower().startswith('0b'): return int(v, 2)
        if v.startswith('0'): return int(v, 8)
        return int(v)
    neg = sval.startswith('-')
    assert((v:=_parse(sval[neg:])) >= 0), "double negative"
    return v * (-1 if neg else 1)
    


class Tuple(Composite):

    name = 'tuple'

    def simple_parse(self, sval, kw):
        assert(not kw)
        svals = sval.split(',')
        assert (len(self.subs)==1 or len(self.subs) == len(svals)), f"Argument data {svals!r} does not match the size of the type '{self}'."
        v = []
        for arg, sub in zip(svals, [self.subs[0]]*len(svals) if len(self.subs) == 1 else self.subs):
            v.append(sub(0, ['\\'+arg], Param.unset)[0])
        return tuple(v)



@param_type('float')
def Float(self, sval, _):
    return float(sval)



@param_type('str')
def Str(self, sval, kw):
    assert(not kw)
    return sval



class Bool(ParamType):

    name = 'bool'

    def simple_parse(self, sval, kw):
        names = ['true','t','yes','y','on','1',  'false','f','no','n','off','0']
        assert(sval.lower() in names), f"Must be one of (case insensitive):  { ', '.join('/'.join(x) for x in zip(names,names[:len(names)/2]))}"
        return names.index(sval.lower()) < len(names)/2
    
    def parse(self):
    # If we run out of args.  It is fine for a bool to be at the end when parsing as keyword, otherwise move on to keywords
        if not self.args: return (Param.unset, True) if isinstance(self.key_arg, int) else (self.change_v(True), False) 
    # Use the normal simple_parse mechanism for `-` and non kw arguments
        if self.args[0] == '-' or not _is_kw(self.args[0]):
            v, kw = super().parse()
            return self.change_v(v), kw
    # If we are parsing as a positional parameter then move to parsing keywords
        if isinstance(self.key_arg, int): return Param.unset, True
    # If we are parsing as a keyword parameter then treat it as true and move on
        return self.change_v(True), False
    
    def change_v(self, v):
        if not v: return v
        v = (self.v or 0) + v
        return v if v > 1 else True



def composite(sup, *subs):
    def _fn():
        return sup(*[s() for s in subs])
    return _fn



from .errors import ParseError
