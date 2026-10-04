import socket, time, subprocess, sys
from pathlib import Path
from .sys_tool import SysTool
from cli import ConfigVar, UsageError, Cmd
from libclipy.core.pretty import CLR
from dataclasses import dataclass, KW_ONLY

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def port_closed(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)): return True


class GCloud(SysTool):
    init_defaults = dict(project_id='', zone='')
    sub_commands = ['compute', 'services', 'projects']
    cmd = ConfigVar('gcloud_path The path to the gcloud executable', default='gcloud')
    version = ConfigVar('gcloud_version The desired config version for gcloud', default='511')
    version_probe = r'^Google Cloud SDK (?P<v0>\d+).(?P<v1>\d+).(?P<v2>\d+)$'
    default_project_id = ConfigVar('gcloud_project_id The default project id to use', default='')
    default_zone = ConfigVar('gcloud_zone The default zone to use', default='')
    iap_ssh_key = ConfigVar('gcloud_iap_ssh_key The ssh key used when connecting to an instance through an iap tunnel', default='local/iap_ssh_key')
    instance_cache = ConfigVar('gcloud_instance_cache A json cachefile for instance/zone mappings', default='local/instance_zone_cache.json')

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
            raise UsageError(f"Can't use gcloud with target {target.v!r}")
        if not self.project_id or self.project_id is True: self.project_id = GCloud.default_project_id.v 
        if not self.zone: self.zone = GCloud.default_zone.v


    @property
    def region(self):
        return self.zone.rsplit('-',1)[0] if self.zone else ''


    @property
    def profile(self):
        if not hasattr(self, '_profile'):
            self._profile = self.compute('os-login', 'describe-profile', json=True).call()
        return self._profile
    

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


    def iap_tunnel(self, **kwargs):
        return IAPTunnel(self, **kwargs)


    def __call__(self, *cmd, json=False, **kwargs):
        cmd = [self.cmd.v, *cmd]
        if self.project_id: cmd[1:1] = [f'--project', self.project_id]
        return Cmd(*cmd,'--format=json', **kwargs).on(0,'json') if json else Cmd(cmd=cmd, **kwargs)


    def instance_to_zone(self, name):
        import json
        try:
            with open(self.instance_cache.v, 'r', encoding='utf8') as f: return json.load(f)[name]
        except:
            data = {v['name']:v['zone'].rsplit('/',1)[-1] for v in self.compute('instances', 'list', json=True).call()}
            with open(self.instance_cache.v, 'w', encoding='utf8') as f: json.dump(data, f, ensure_ascii=False)
            if name not in data: raise UsageError(f"Instance {name!r} not found:  {' '.join(data.keys())}")
            return data[name]



@dataclass
class IAPTunnel():
    gcloud: GCloud
    _: KW_ONLY
    port: int = 0
    remote_port: int = 22
    vm_name: str = ''

    def __post_init__(self):
        if not self.port: self.port = get_free_port()


    def _args(self):
        return ('compute', 'start-iap-tunnel', self.vm_name, self.remote_port, '--local-host-port', f'localhost:{self.port}', '--zone', self.gcloud.instance_to_zone(self.vm_name))


    def exec(self):
        return self.gcloud.exec(*self._args())


    def __enter__(self):
        if not port_closed(self.port): return self
        cmd = self.gcloud.prepare_call(*self._args())[0]
        self.proc = subprocess.Popen(cmd)#, stderr=subprocess.DEVNULL)
        while port_closed(self.port): time.sleep(0.1)
        return self


    def __exit__(self, *args):
        if hasattr(self, 'proc'):
            self.proc.kill()
            self.proc.communicate()


    def rsync(self):
        from .rsync import Rsync
        return Rsync().remote(f'{self.gcloud.username}@127.0.0.1:{self.port}', i=self.gcloud.ssh_key)
        

    def ssh(self):
        return SSHSession(self, self.gcloud, sftp=False)



@dataclass
class SSHSession():
    iap: IAPTunnel
    gcloud: GCloud
    _: KW_ONLY
    sftp: bool = True
    
    def __enter__(self):
        import paramiko
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            hostname = 'localhost',
            port = self.iap.port,
            username = self.gcloud.username,
            key_filename = str(self.gcloud.ssh_key),
            allow_agent = False,
            look_for_keys = False
        )
        self.sftp = self.ssh.open_sftp() if self.sftp else None
        return self


    def __exit__(self, *args):
        if self.sftp is not None: self.sftp.close()
        self.ssh.close()


    def __call__(self, cmd, *, pty=False):
        channel = self.ssh.get_transport().open_session()
        print(f"  $ {cmd}")
        if pty: channel.get_pty()
        channel.exec_command(cmd)
        exit_code, output = None, [b'', b'']
        while exit_code is None:
            exit_code = channel.recv_exit_status() if channel.exit_status_ready() else None
            for i in range(2):
                while (channel.recv_stderr_ready if i else channel.recv_ready)():
                    data = (channel.recv_stderr if i else channel.recv)(4096)
                    if pty: sys.stdout.write(data.decode())
                    else: output[i] += data
            time.sleep(0.01)
        if not pty:
            sys.stdout.write(output[0].decode())
            sys.stderr.write(output[1].decode())
        if exit_code: raise Exception(f"Cmd failed {exit_code}: {cmd}")

