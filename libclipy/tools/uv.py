from cli import ConfigVar
from .sys_tool import SysTool


class Uv(SysTool):

    sub_commands = ['pip', 'venv']
    version_probe = r'^uv (?P<v0>\d+)\.(?P<v1>\d+)\.(?P<v2>\d+).*$'
    cmd = ConfigVar('Uv.cmd The path to the uv executable', default='uv')
    version = ConfigVar('Uv.version The required version of openssl', default='0.13.5')

    @classmethod
    def install_help_generic(self):
        return ['See installation instructions: https://docs.astral.sh/uv/getting-started/installation/']
