from .core.config import target, verbosity, cfg, ConfigVar, Target, env
from .core.command.dfn import cmd, pip
from .core.command.param import ParamType, param_type

class Color():
    def __init__(self):
        self.color_on = True

    def __getattr__(self, a):
        if not self.color_on: return ''
        a = {'a':'1;30', 'la':'0;37', 'r':'0;31', 'lr':'1;31', 'g':'0;32', 'lg':'1;32', 'o':'0;33','y':'1;33','b':'0;34','lb':'1;34','m':'0;35', 'lm':'1;35', 'c':'0;36', 'lc':'1;36', 'bld':'1','w':'1','x':'0'}[a]
        return '\x1b['+a+'m'

CLR = Color()
