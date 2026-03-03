import os, re, asyncio
from cli import CLR, print, exit, run, UsageError, Text
from subprocess import PIPE, DEVNULL



class Singleton(type):
    def __new__(self, name, bases, dict):
        dict['_instances'] = {}
        return super().__new__(self, name, bases, dict)


    def __call__(base, *args, **kwargs):
        name = f"{base.__name__}__{hex(abs(hash(args)))}"
        try:
            cls_inst = base._instances[name]
        except KeyError:
            cls_inst = SingletonInstance(name, (base,), {})
            base._instances[name] = cls_inst
            cls_inst.init_once(*args, **kwargs)
        return cls_inst(**kwargs)



class SingletonInstance(Singleton):
    def __call__(self, *args, **kwargs): # override Singleton's __call__ to prevent recursion
        return super(Singleton, self).__call__(*args, **kwargs)

    def init_once(self, *args, **kwargs):
        pass

    def __init__(self, *args, **kwargs):
        pass



class MissingTool(UsageError):
    def __init__(self, tool, got, *, need=None, help=None):
        import platform
        msg = []
        if hasattr(tool, 'used_for'):
            msg += [tool.used_for()]
        need = need or tool.need
        msg = [Text(f"{CLR.y}{tool.__mro__[1].__name__}{CLR.x} requires version >= {CLR.m}{need}{CLR.x}"), '']

        if not got:
            msg += [f'{print.ERR} No version was found.', '']
        else:
            msg += [f'Version {CLR.r}{got}{CLR.x} was found.', '']

        if help:
            msg += help
        else:
            pfm = 'install_help_' + platform.platform().lower().split('-')[0]
            msg += tool.install_help_generic()
            if hasattr(tool, pfm): msg += [''] + getattr(tool, pfm)()
        super().__init__(*msg)
        



class SysTool(metaclass=Singleton):
    version_cmd = None

    @classmethod
    def version_fail(self, have, need):
        print.ln(print.ERR, f"Invalid version for {self.__name__.split('__')[0]}", ['']*2, f"have: {have}", ['']*2, f"need: {need}")
        exit(1)


    @classmethod
    def init_once(self, **kwargs):
        got = run(self.version_cmd or (self.cmd, '--version'), msg=None, if_0='utf8,utf8,', or_else='null,null,')
        try:
            assert(got)
            got = (got[0] + got[1]).strip()
            m = re.match(self.version_re, got, re.I | re.MULTILINE)
            for i, v in enumerate(self.min_version): 
                if (v_have := int(m.groupdict().get(f'v{i}',-1))) > v: return
                assert (v_have == v)
        except Exception as e:
            raise MissingTool(self, got, need='.'.join(map(str, self.min_version)))
        
    
    def __getattr__(self, cmd):
        return partial(self, cmd.replace('_','-'))

    
    def __call__(self, *cmd, **kwargs):
        return run(self.prepare_call(*cmd), **kwargs)


    def prepare_call(self, *cmd):
        return (type(self).cmd, *cmd)


from functools import partial
