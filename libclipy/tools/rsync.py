from .sys_tool import SysTool
from ..CLI import config_var

class Rsync(SysTool):
    ''' Copy files to a remote machine accessible with ssh.

    Examples:

        rsync = Rsync().remote('user@remote:2222')
        rsync.sync('bob', 'file1.txt', 'folder/file2.txt', 'empty_folder/')
    '''
    @config_var
    def version(v='3'):
        ''' The desired version rsync '''
        return str(v)
    
    version_probe = r'^rsync\s+version\s+(?P<v0>\d+).(?P<v1>\d+).(?P<v2>\d+)'
    cmd = 'rsync'

    def __init__(self, remote=None, args=None, links=True, i=None, host_check=False):
        self.args = ['-vz', '-rtp', '-l' if links else '-L']
        if args: self.args += args
        remote = remote.rsplit(':',1)
        ssh = 'ssh'
        if len(remote) == 2: ssh += f' -p {remote[1]}'
        if i is not None: ssh += f' -i {i}'
        if not host_check: ssh += ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        self.args += ['-e', f'{ssh} {remote[0]}']


    def sync(self, dest, *src, chown=None, delete=True, chdir='.', dry=False, **kwargs):
        ''' Sync the files to the destination.

        Note that files cannot be renamed because the destination `dest` is always a folder (so you cannot specify a destination filename)
        
        Parameters:
            dest
                This is the destination *folder*.
                The contents of the destination folder will modified to match the `src` files.
                If it is not an absolute path then it is relative to the user's home directory.
            src
                A list of files that should exist 
                If a file starts with an exclamation point then that pattern of files will be protected (P) in the destination folder.

                !logs/***    This will make sure the logs folder will never be deleted (even if it is empty)
        '''
        cmd = []
        if chown: cmd += ['--rsync-path', 'sudo rsync', '--chown', chown]
        if delete: cmd += ['--delete', '--delete-excluded']
        if dry: cmd += ['--dry-run']
    # Build the filter
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
        # All folders must be explicitly included (or they will get pruned and no files under the will be found)
            def _ensure_directory(f, parts, have=set()):
                if not parts or (d:=f"{Path(*parts)}/") in have: return
                _ensure_directory(f, parts[:-1], have)
                have.add(d)
                f.write(f'+ {d}\n')
        # Build the filter file
            with open(tmp.name, 'w') as f:
                for s in src:
                    if s.startswith('!'):
                        f.write(f'P {s[1:]}\n')
                    else:
                        _ensure_directory(f, Path(s).parts[:-1])
                        f.write(f'+ {s}\n')
                f.write('- *\n')
        # Run the sync
            self(*self.args, *cmd, '--filter', f'. {tmp.name}', chdir + ('' if chdir.endswith('/') else '/'), f":{dest}", **kwargs)


    def copy(self, *args, **kwargs):
        ''' Same as `sync()` but with `delete` set to False
        '''
        kwargs['delete'] = False
        return self.sync(*args, **kwargs)


from pathlib import Path
import tempfile