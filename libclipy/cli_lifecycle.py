import tempfile, os, json, time
from cli import Command, Cmd, env_prefix
from config import system, target
from pathlib import Path
from libclipy.core.venv import Venv
from libclipy.core.errors import CmdError


class SetupJournal():
    # You can add new cmds to the **end** of `CMD` without changing the version.
    # Otherwise change the SETUP_VERSION with any change to CMDS so that you don't accedentally run setup in an incompatable environment.
    version = 0
    deploy_start = 7 # The index of the `systemctl stop app` command

    def __init__(self):
        self.path = Path('/opt/app/setup_journal.json')
        try:
            self.info = json.loads(self.path.read_text())
        except FileNotFoundError:
            self.info = {'version':SetupJournal.version, 'runs':[]}
        if self.info['version'] != SetupJournal.version:
            raise ValueError(f"This instance has already been setup with conflicting version {SetupJournal.version}: {self.info}")

    def begin(self, *, commit, start):
        from datetime import datetime
        if start < 0: start = self.info['runs'][-1]['stop'] if self.info['runs'] else 0
        self.info['runs'].append({'commit':commit, 'start':start, 'when':datetime.now().isoformat(), 'stop':start})
        self.save()
        return start

    def step(self):
        self.info['runs'][-1]['stop'] += 1
        self.save()

    def save(self):
        if not self.path.parent.exists():
            Cmd('mkdir', '-p', self.path.parent).sudo().call()
        write_root_file(self.path, json.dumps(self.info))
    


def write_root_file(path, *lines, chmod='644', append=False):
    with tempfile.NamedTemporaryFile() as f:
        f.write((Cmd('cat', path).sudo().call('bin') if append else b'') + ('\n'.join(lines)+'\n').encode())
        f.flush()
        Cmd('cp', f.name, path).sudo().call()
        if chmod is not None: Cmd('chmod', chmod, path).sudo().call()



def _install_app_service(*, log_file):
    lines = [
        '[Unit]', 'Description=App Service', 'After=network.target',
        '', '[Service]', 'ExecStart=/usr/local/bin/app run', 'KillSignal=SIGINT', 'TimeoutStopSec=15s', 'Restart=always',
        # FIXME: Move away from letting systemd capture the output and let our app write (and rotate) its own files automatically
        f'StandardOutput=append:{log_file}', f'StandardError=append:{log_file}', 
        '', '[Install]', 'WantedBy=multi-user.target'
    ]
    write_root_file('/etc/systemd/system/app.service', *lines)
    Cmd('systemctl', 'daemon-reload').sudo().say().call()
    Cmd('systemctl', 'enable', 'app.service').sudo().say().call()


def _install_app(*, log_file, **vars):
    for venv in Venv.all(): venv.venv_path() # Build them all now because app:app won't be able to write to core/info.json
    Cmd('rsync', '-a', '--delete', '--delete-excluded', '--filter', 'P /setup_journal.json', '--chown', 'root:root', '--exclude', '/local', '.', '/opt/app/').sudo().say().call()
    readme = ['The app is running as a service `app`:','  $ sudo systemctl status app','',
              'Call `app` for the installed /opt/app/cli.py:','  $ app -h','',
             f"Logs are in {log_file}"]
    with open(Path('~').expanduser()/'README.md', 'w') as f: f.write('\n'.join(readme) + '\n')
    Cmd('mkdir', '-p', log_file.parent).sudo().call()
    Cmd('touch', log_file).sudo().say().call()
    Cmd('chown', '-R', 'app:app', vars['_LOCAL_ROOT']).sudo().call()
    Cmd('chmod', '2770', vars['_LOCAL_ROOT']).sudo().call()
    Cmd('chmod', '-x', '/opt/app/cli.py').sudo().call()
    exported = [f"export {(env_prefix+k[1:] if k.startswith('_') else k)}={v!r}" for k,v in vars.items()]
    write_root_file('/usr/local/bin/app', '#!/bin/sh', *exported, 'exec sudo -E -u app -g app python3 /opt/app/cli.py "$@"', chmod='755')


def _setup_log_rotation(*, log_file): # FIXME This can be removed when our app can rotate its own files
    lines = [f"{log_file} {{", 'size 4096k', 'rotate 200', 'compress', 'copytruncate', 'dateext', 'dateformat .%Y-%m-%d-%H%M','}']
    write_root_file('/etc/logrotate.d/app', *lines)
    

def _diable_apt_systemd():
    write_root_file('/usr/sbin/policy-rc.d', '#!/bin/sh', 'exit 101', chmod='755')


def _useradd(*, home):
    try:
        Cmd('id','app').call()
    except CmdError:
        Cmd('useradd', '-r', '-g', 'app', '-M', '-s', '/sbin/nologin', '-d', home, 'app').sudo().call()



@Command(system='cloud')
def setup(*, start=-1, stop=0, git_commit=''):
    ''' Setup this project for the `system` that it is running on.
    
    Parameters:
        --start
            Set the first command to start executing
        --stop
            Stop setting up before this command.  By default, setup all commands.
    '''
    APT_PACKAGES = 'curl libaio1t64 nginx certbot python3-certbot-nginx'.split(' ')
    vars = dict(_TARGET='.'.join(target.v), _SYSTEM=system.v, _LOCAL_ROOT='/var/opt/app', _VENV_ROOT='/var/opt/app/.python', UV_CACHE_DIR='/var/opt/app/.uv', PYTHONUNBUFFERED=1)
    log_file = Path(vars['_LOCAL_ROOT'])/'log/output.log'
    CMDS = [
        (_useradd, {'home':vars['_LOCAL_ROOT']}),
        Cmd('apt-get', 'update').env(DEBIAN_FRONTEND='noninteractive').sudo(),
        Cmd('apt-get', 'full-upgrade', '-y').env(DEBIAN_FRONTEND='noninteractive').sudo(),
        (_diable_apt_systemd, {}),
        Cmd('apt-get', 'install', '-y', *APT_PACKAGES).env(DEBIAN_FRONTEND='noninteractive').sudo(),
        (_setup_log_rotation, {'log_file':log_file}),
        (_install_app_service, {'log_file':log_file}),
        Cmd('systemctl', 'stop', 'app').sudo(),
        (_install_app, {'log_file':log_file}|vars),
        Cmd('app', 'pre-run'),
        Cmd('systemctl', 'start', 'app').sudo(),
    ]
    journal = SetupJournal()
    start = journal.begin(commit=git_commit, start=start)
# Run commands from the checkpoint
    print(f"Starting setup from #{start}")
    for cmd in CMDS[start:(stop or len(CMDS))]:
        if isinstance(cmd, Cmd):
            cmd().say().call()
        else:
            cmd[0](**cmd[1])
        journal.step()



@Command(system='cloud')
def pre_run():
    ''' Executed before run to setup as app (only useful in the 'cloud' system)
    '''
    for venv in Venv.all(): venv.venv_path()



@Command()
async def run():
    ''' Run everything the project needs to operate.

    This will be called automatically from the systemd service configuration file when running on the `cloud` system.
    '''
    from .cli_web import server, nginx
    import logging
    logging.getLogger('run')('Starting...', tags=['service_start', '.'.join(target.v)], obj={k:v for k,v in os.environ.items() if k.startswith(env_prefix)})
    await Cmd.all(server().call_async(), nginx().call_async())
