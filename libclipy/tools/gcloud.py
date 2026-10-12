import socket, time, subprocess, sys
from pathlib import Path
from .sys_tool import SysTool
from cli import ConfigVar, UsageError, Cmd
from libclipy.core.pretty import CLR
from contextlib import contextmanager

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def port_closed(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)): return True


class GCloud(SysTool):
    init_defaults = dict(project_id='', zone='')
    sub_commands = ['compute', 'services', 'projects', 'config']
    version_probe = r'^Google Cloud SDK (?P<v0>\d+).(?P<v1>\d+).(?P<v2>\d+)$'
    cmd = ConfigVar('GCloud.cmd The path to the gcloud executable', default='gcloud')
    version = ConfigVar('GCloud.version The desired config version for gcloud', default='511')
    default_project_id = ConfigVar('GCloud.default_project_id The default project id to use', default='')
    default_zone = ConfigVar('GCloud.default_zone The default zone to use', default='')
    iap_ssh_key = ConfigVar('GCloud.iap_ssh_key The ssh key used when connecting to an instance through an iap tunnel', default='local/iap_ssh_key')
    instance_cache = ConfigVar('GCloud.instance_cache A json cachefile for instance/zone mappings', default='local/instance_zone_cache.json')

    @classmethod
    def install_help_generic(self):
        return ["Install instructions: https://cloud.google.com/sdk/docs/install"]

    @classmethod
    def install_help_macos(self):
        return ["$ brew install --cask gcloud-cli"]


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.project_id is True and not GCloud.default_project_id.v or self.zone is True and not GCloud.default_zone.v:
            from config import target
            raise UsageError(f"Can't use gcloud with target {target.v!r}\nMake sure to set {CLR.y}default_project_id{CLR.x} and {CLR.y}default_zone{CLR.x}")
        if not self.project_id or self.project_id is True: self.project_id = GCloud.default_project_id.v 
        if not self.zone: self.zone = GCloud.default_zone.v


    @property
    def region(self):
        return self.zone.rsplit('-',1)[0] if self.zone else ''


    @property
    def profile(self):
        import json
        from config import local_root
        from libclipy.core.errors import CmdError
        profiles = None
        profile_path = local_root.path('gcloud_profiles.json')
        try:
            account = self.config('get-value', 'account').call('utf8').strip()
            profiles = json.loads(profile_path.read_text())
            return profiles[account]
        except CmdError: raise
        except:
            if profiles is None: profiles = {}
            profiles[account] = self.compute('os-login', 'describe-profile', json=True).say().call()
            profile_path.write_text(json.dumps(profiles))
        return profiles[account]
    

    @property
    def username(self):
        return self.profile['posixAccounts'][0]['username']


    @property
    def ssh_key(self):
        key = Path(GCloud.iap_ssh_key.v)
        if not key.exists():
            import paramiko
            rsa = paramiko.RSAKey.generate(2048)
            rsa.write_private_key_file(key)
            key.chmod(0o600)
            (pub:=key.with_suffix('.pub')).write_text(f"{rsa.get_name()} {rsa.get_base64()}\n")
            self.compute('os-login', 'ssh-keys', 'add', f"--key-file={pub}").call()
        return key


    def iap(self, **kwargs):
        return IAPTunnel(self, **kwargs)


    @contextmanager
    def ssh(self, **kwargs):
        kwargs.setdefault('remote_port',22)
        with self.iap(**kwargs) as iap:
            with iap.ssh() as ssh:
                yield ssh


    def instance_to_zone(self, name):
        import json
        try:
            with open(self.instance_cache.v, 'r', encoding='utf8') as f: return json.load(f)[name]
        except:
            data = {v['name']:v['zone'].rsplit('/',1)[-1] for v in self.compute('instances', 'list', json=True).call()}
            with open(self.instance_cache.v, 'w', encoding='utf8') as f: json.dump(data, f, ensure_ascii=False)
            if name not in data: raise UsageError(f"Instance {name!r} not found:  {' '.join(data.keys())}")
            return data[name]


    def __call__(self, *cmd, json=False, **kwargs):
        cmd = [self.cmd.v, *cmd]
        if self.project_id: cmd[1:1] = [f'--project', self.project_id]
        return Cmd(*cmd,'--format=json', **kwargs).on(0,'json') if json else Cmd(*cmd, **kwargs)



class IAPTunnel():
    ''' This provides a local port that tunnels to a remote gce instance.
    FIXME make this a dep that provides the port service.
    '''
    def __init__(self, gcloud, *, port=0, remote_port=22, vm_name=''):
        self.gcloud, self.remote_port, self.vm_name = gcloud, remote_port, vm_name
        self.port = port or get_free_port()


    @property
    def cmd(self):
        return self.gcloud(*('compute', 'start-iap-tunnel', self.vm_name, self.remote_port,
                             '--local-host-port', f'localhost:{self.port}',
                             '--zone', self.gcloud.instance_to_zone(self.vm_name)))


    def __enter__(self):
    # If this port is already open, then just use that one
        if not port_closed(self.port): return self
    # Open it and wait for the port to be ready
        self._iter = iter(self.cmd.say().iter_sync())
        try:
            for i in range(1,50):
                if not port_closed(self.port): break
                if not i%10: print(f"Waiting for localhost port {self.port}...")
                time.sleep(0.1)
            else: raise ValueError(f"The port {self.port} never opened")
        except BaseException:
            self._iter.close()
            raise
        return self


    def __exit__(self, *args):
        if hasattr(self, '_iter'): self._iter.close()


    def rsync(self):
        from .rsync import Rsync
        return Rsync(remote=f'{self.gcloud.username}@127.0.0.1:{self.port}', i=self.gcloud.ssh_key)
        

    def ssh(self):
        return SSHSession(self, self.gcloud, sftp=False)



class SSHCmd(Cmd):
    def __init__(self, transport, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transport = transport

    def call(self, fmt=None, value=None, *, pty=False, stdin=None):
        ''' Run a shell command using the user's login shell program.

        Parameters:
            pty | default False
                This requests a pseudo terminal.
                A pty provides a 'user interactive' environment and is required by some commands like sudo.

                Without a pty, the output might get heavily buffered and you won't see the output realtime.
                With a pty, the stderr gets merged into stdout.

                Run without a pty if possible.
        '''
        c = self._get_conditions(fmt, value)
        channel = self.transport.open_session()
        channel.setblocking(0)
        if pty: channel.get_pty()
        channel.exec_command(self.shell_cmd)
        try:
            out = {k:bytearray() if c.channels[k] == 'buf' else None for k in ('stdout', 'stderr')}
            def _need_wait(src, postfix=''):
                if not getattr(channel, f'recv{postfix}_ready')(): return True
                data = getattr(channel, f'recv{postfix}')(4096)
                if out[src] is None:
                    if c.channels[src] != 'null': getattr(sys, src).buffer.write(data)
                else:
                    out[src].extend(data)
        # Wait for all output and the exit code
            while True:
                if not (_need_wait('stdout') and _need_wait('stderr', '_stderr')): continue
                if channel.exit_status_ready(): break
                time.sleep(0.1)
        except BaseException:
            # FIXME when paramiko implements send_signal('SIGTERM') we can kill our process properly
            raise
    # Get the returncode and maybe raise
        return c.return_value(self, channel.recv_exit_status(), out)

    
    def iter_sync(self, **kwargs):
        raise NotImplementedError("Not usable in an SSH Cmd")
    
    def iter_aync(self, **kwargs):
        raise NotImplementedError("Not usable in an SSH Cmd")



class SSHSession():
    def __init__(self, iap, gcloud, *, sftp=True):
        self.iap, self.gcloud, self.sftp = iap, gcloud, sftp

    
    def __enter__(self):
        import paramiko
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        tries = 5
        while True:
            try:
                print(f"Connecting to {self.gcloud.username}@localhost:{self.iap.port}")
                self.ssh.connect(
                    hostname = 'localhost',
                    port = self.iap.port,
                    username = self.gcloud.username,
                    key_filename = str(self.gcloud.ssh_key),
                    allow_agent = False,
                    look_for_keys = False
                )
                break
            except paramiko.ssh_exception.NoValidConnectionsError as e:
                if tries == 0: raise e from None
                tries -= 1
                time.sleep(1)
        self.ssh_transport = self.ssh.get_transport()
        self.sftp = self.ssh.open_sftp() if self.sftp else None
        return self


    def __exit__(self, *args):
        if self.sftp is not None: self.sftp.close()
        self.ssh.close()


    def cmd(self, *args, **kwargs):
        ''' This returns a subclass of `Cmd` that overrides the `call()` method to use paramiko's channels
        '''
        return SSHCmd(self.ssh_transport, *args, **kwargs)
    