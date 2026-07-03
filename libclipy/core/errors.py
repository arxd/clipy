
class PrettyException(Exception):
    ''' This is an Exception that has a pretty() method to render itself.
    '''
    def __init__(self, msg=None, **kwargs):
        if msg is not None: kwargs['msg'] = msg
        for k,v in kwargs.items(): setattr(self, k,v)

    def __str__(self):
        return ('\n'.join(self.msg) if isinstance(self.msg, (list,tuple)) else self.msg) if hasattr(self, 'msg') else repr(self)

    def __repr__(self):
        s = f"{self.__class__.__name__}("
        args = [f'{k}={v!r}' for k,v in self.__dict__.items()]
        return s+ ', '.join(args) + ')'
    
    def pretty(self):
        print(str(self))



class UsageError(PrettyException):
    ''' This is a user-rectifiable error.
    
    They should do what they are told in the error message and then try again.
    '''
