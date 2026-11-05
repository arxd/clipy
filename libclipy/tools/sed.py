from pathlib import Path
from cli import ConfigVar
from .sys_tool import SysTool

class Sed(SysTool):
    ''' The system sed tool.
    '''
    version = None
    version_probe = None
    cmd = ConfigVar('Sed.cmd The path to the sed executable', default='sed')

    def sub(self, path, *patterns):
        patterns = [item for p in patterns for item in ('-e', p)]
        Path(path).write_text(self(*patterns, path).call('utf8'), encoding='utf8')
