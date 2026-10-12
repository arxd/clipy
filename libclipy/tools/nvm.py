import shlex
from .sys_tool import SysTool
from cli import ConfigVar, Cmd, Command, UsageError
from libclipy.core.pretty import CLR


@Command()
def nvm(*args):
    ''' Run nvm exec ... versioned correctly (.nvmrc) for this project
    '''
    return NVM()(*args).exec()



@Command()
def firebase(*args):
    ''' Run nvm exec firebase ... versioned correctly (.nvmrc) for this project
    '''
    return Firebase()(*args).exec()



class Firebase(SysTool):
    init_defaults = dict(project_id='')
    version_probe = lambda _: NVM().firebase('--version').on(0,'utf8'), r'^(?P<v0>\d+).(?P<v1>\d+).(?P<v2>\d+)$'
    version = ConfigVar('Firebase.version The desired config version for firebase', default='15.30')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from .gcloud import GCloud
        if self.project_id is True and not GCloud.default_project_id.v:
            from config import target
            raise UsageError(f"Can't use firebase with target {target.v!r}\nMake sure to set {CLR.y}GCloud.default_project_id{CLR.x}")
        if not self.project_id or self.project_id is True: self.project_id = GCloud.default_project_id.v 

    def __call__(self, *args, **kwargs):
        if self.project_id: args = [args[0], '--project', self.project_id, *args[1:]]
        return NVM().firebase(*args, **kwargs)

    @classmethod
    def install_help_generic(self):
        return ['Install Firebase CLI via NVM either globally:', '  $ ./cli.py nvm npm install -g firebase-tools', 'Or locally to the project:', '   $ ./cli.py nvm npm install --save-dev firebase-tools']



class NVM(SysTool):
    sub_commands = ['npm', 'firebase']
    version_probe = lambda _: Cmd('sh', '-c', f'source $NVM_DIR/nvm.sh; nvm --version').on(0,'utf8'), r'^(?P<v0>\d+).(?P<v1>\d+).(?P<v2>\d+)$'
    version = ConfigVar('NVM.version The desired config version for nvm', default='0.40')
    
    @classmethod
    def install_help_generic(self):
        return ['https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating']

    def __call__(self, *args, **kwargs):
        return Cmd('sh', '-c', f"source $NVM_DIR/nvm.sh; nvm exec {shlex.join(map(str, args))}", **kwargs)

