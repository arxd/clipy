from cli import Target, ConfigVar
from libclipy.cli_grep import grep_groups
from libclipy.cli_workflow import codes
from libclipy.core.config import verbosity, work_root, format_out, target

@Target()
def local():
    grep_groups.default = {'tests':r'.*/_test.*', 'docs':r'docs/.*', 'core':r'libclipy/core/.*', 'web':r'(libclipy/)?web/.*', 'tools':r'libclipy/tools/.*', 'libclipy':r'libclipy/.*'}
    
    codes.default = {
        '': ('', ['local', 'config.py']),
        'd': ('documentation', ['docs', 'README.rst']),
        'c': ('libclipy', ['libclipy', 'cli.py']),
        'w': ('web', ['web']),
    }
