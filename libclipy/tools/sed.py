from cli import ConfigVar
from .sys_tool import SysTool

class Sed(SysTool):
    ''' The system sed tool.
    '''
    version = None
    version_probe = None
    cmd = ConfigVar('sed_path The path to the sed executable', default='sed')

    def sub(self, path, *patterns):
        patterns = [item for p in patterns for item in ('-e', p)]
        out = self(*patterns, path, msg=False, if_0="utf8,,")
        with open(path,'w') as f: f.write(out)
