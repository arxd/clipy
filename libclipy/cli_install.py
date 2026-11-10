from cli import Command, ConfigVar

default_install_remote = ConfigVar('default_install_remote The default argument for `remote` when calling the install command')

@Command()
def install(remote=None):
    ''' Rsync this project directly to a host with rsync

    Parameters:
        <remote>, --remote <remote>
            Deploy to this host  (name@hostname:port)
    '''
    from libclipy.tools.git import Git
    from libclipy.tools.rsync import Rsync
    from cli import name, project_root
    Rsync(remote=remote or default_install_remote.v, chdir=project_root).sync(name, *Git().ls())
