import socket, time, subprocess, sys, json
from pathlib import Path
from .sys_tool import SysTool
from .make import Make
from ..CLI import CLR, config_var

@config_var
def localhost_iap_port(v=2831):
    ''' The default port used on the localhost when an IAP tunnel is opened to a remote VM'''
    return int(v)


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
    
    @config_var
    def version(v='511'):
        ''' The desired gcloud version '''
        return str(v)


    version_probe = r'^Google Cloud SDK (?P<v0>\d+).(?P<v1>\d+).(?P<v2>\d+)$'
    cmd = 'gcloud'


    @classmethod
    def install_help_generic(self):
        return ["Install instructions: https://cloud.google.com/sdk/docs/install"]


    @property
    def region(self):
        return self.zone.rsplit('-',1)[0] if self.zone else ''


    def iap_tunnel(self, vm_name, **kwargs):
        return IAPTunnel(gcloud=self, vm_name=vm_name, **kwargs)


    @property
    def profile(self):
        if not hasattr(self, '_profile'):
            self._profile = self.compute('os-login', 'describe-profile', '--format=json', if_0='json,,', msg=None)
        return self._profile
    

    @property
    def username(self):
        return self.profile['posixAccounts'][0]['username']


    @property
    def ssh_key(self):
        import paramiko
        if hasattr(self,'_ssh_key'): return self._ssh_key
        self._ssh_key = Path("local/iap_ssh_key")
        if not self._ssh_key.exists():
            print(f"Generate SSH Key: {self._ssh_key}")
            key = paramiko.RSAKey.generate(2048)
            key.write_private_key_file(self._ssh_key)
            pub = f"{key.get_name()} {key.get_base64()}"
            with open(self._ssh_key.with_suffix('.pub'), 'w') as f: f.write(pub+'\n')
            self.compute('os-login', 'ssh-keys', 'add', f"--key-file={self._ssh_key.with_suffix('.pub')}")
        return self._ssh_key


    def prepare_call(self, *cmd):
        return (self.cmd, *cmd) if not self.project_id else (self.cmd, f'--project', self.project_id, *cmd)




class IAPTunnel():
    def __init__(self, **kwargs):
        kwargs.setdefault('remote_port', 22)
        kwargs.setdefault('port', None)
        
        for k,v in kwargs.items(): setattr(self, k, v)
        if not hasattr(self, 'zone'): self.zone = self.gcloud.zone
        if self.port is None: self.port = localhost_iap_port.v


    def exec(self):
        self.gcloud.compute('start-iap-tunnel', self.vm_name, self.remote_port, '--local-host-port', f'localhost:{self.port}', '--zone', self.zone, exec=True)


    def __enter__(self):
        self.port = get_free_port() if self.port is None else int(self.port)
        if port_closed(self.port):
            assert(self.vm_name), f"Instance name must be specified if no local iap-tunnel is running."
            print(f"Starting iap-tunnel to {CLR.m}{self.vm_name!r}:{self.remote_port}{CLR.x} from {CLR.c}localhost:{self.port}{CLR.x}")
            cmd = self.gcloud.prepare_call('compute', 'start-iap-tunnel', self.vm_name, str(self.remote_port), '--local-host-port',f'localhost:{self.port}', '--zone', self.zone)
            self.proc = subprocess.Popen(cmd)#, stderr=subprocess.DEVNULL)
            while port_closed(self.port): time.sleep(0.2)
        else:
            print(f"iap-tunnel already running on localhost:{self.port}")
        return self


    def __exit__(self, *args):
        if hasattr(self, 'proc'):
            self.proc.kill()
            self.proc.communicate()


    def rsync(self):
        from .rsync import Rsync
        return Rsync().remote(f'{self.gcloud.username}@127.0.0.1:{self.port}', i=self.gcloud.ssh_key)
        

    def ssh(self):
        return SSHSession(iap=self, sftp=False)




class SSHSession():
    def __init__(self, **kwargs):
        for k,v in kwargs.items(): setattr(self, k, v)
    

    def __enter__(self):
        import paramiko
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            hostname = 'localhost',
            port = self.iap.port,
            username = self.iap.gcloud.get_username(),
            key_filename = str(self.iap.gcloud.ssh_key),
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




@Make.inline()
def AddBackends(self):
    gcloud = GCloud()
    cxns = []
    negs = gcloud.compute('network-endpoint-groups', 'list', '--format=json', if_0='json,,', msg=None)
    def _neg(k):
        for n in negs:
            if k == n['selfLink']: return n['name']
    for backend_service in gcloud.compute('backend-services', 'list', '--format=json', if_0='json,,', msg=None):
        for backend in backend_service.get('backends',[]):
            cxns.append( (backend_service['name'], f"--network-endpoint-group={_neg(backend['group'])}") )
    for args in self.deps:
        if args[:2] in cxns: continue
        print(f"Adding {args[1][25:]!r} to {args[0]!r}")
        gcloud.compute('backend-services','add-backend', *args)
    for cxn in cxns:
        if cxn in [d[:2] for d in self.deps]: continue
        print(f"Removing {cxn[1]!r} from {cxn[0]!r}")

    

@Make.inline()
def Nats(self):
    from cli import print
    gcloud = Gcloud()
    have = {}
    for s in gcloud.compute('routers', 'list', '--format=json', if_0='json,,', msg=None):
        for nat in s.get('nats', []):
            have[nat['name']] = nat
    for args in self.deps:
        if args[0] in have: continue
        print(f"Creating routers/nats {args[0]!r}{args[1:]!r}")
        gcloud.compute('routers', 'nats', 'create', *args)
    for name in have:
        if name in [d[0] for d in self.deps]: continue
        print(f"Deleting routers/nats {name!r}")


@Make.inline()
def Services(self):
    gcloud = Gcloud()
    have = {s['config']['name']:s['config'] for s in gcloud.services('list','--enabled', '--format=json', if_0='json,,', msg=None)}
    print(f"Have services: {' '.join(have.keys()&set(self.deps))}")
    enable = set(self.deps) - have.keys()
    if enable:
        print(f"Enabling: {' '.join(enable)}")
        gcloud.services('enable', *enable)
    



def _make_delete(self, *kinds, name_index=0, cmd=None):
    gcloud = Gcloud()
    have = {s['name']:s for s in gcloud.compute(*kinds, 'list', '--format=json', if_0='json,,', msg=None)}
    if cmd is None: cmd = lambda gc, *args: gc.compute(*kinds, 'create', *args)
    for args in self.deps:
        if args[name_index] in have: continue
        print(f"Creating {'/'.join(kinds)} {' '.join(map(str, args))}")
        cmd(gcloud, *args)
    for name in have:
        if name in [d[name_index] for d in self.deps]: continue
        print(f"Manually delete {'/'.join(kinds)} {name!r}:\n   $ gcloud --project={gcloud.project} compute {' '.join(kinds)} delete {name}")


@Make.inline()
def HealthChecks(self): _make_delete(self, 'health-checks', name_index=1)

@Make.inline()
def BackendServices(self):
    def _cmd(gcloud, *args):
        if not args[1].startswith('--security-policy'): return gcloud.compute('backend-services', 'create', *args)
        gcloud.compute('backend-services', 'create', args[0], *args[2:])
        gcloud.compute('backend-services', 'update', *args)
    _make_delete(self, 'backend-services', cmd=_cmd)

@Make.inline()
def HttpsProxies(self): _make_delete(self, 'target-https-proxies')

@Make.inline()
def HttpProxies(self): _make_delete(self, 'target-http-proxies')

@Make.inline()
def UrlMaps(self): _make_delete(self, 'url-maps')

@Make.inline()
def HttpRedirectUrlMaps(self):
    def _cmd(gcloud, name, map):
        cfg = dict(name=name)# kind='compute#urlMap', 
        cfg.update(map)
        gcloud.compute('url-maps', 'import', name, '--global', '--quiet', '--source=-', stdin=json.dumps(cfg), if_0=',,')
    _make_delete(self, 'url-maps', cmd=_cmd)

@Make.inline()
def ForwardingRules(self): _make_delete(self, 'forwarding-rules')

@Make.inline()
def Negs(self): _make_delete(self, 'network-endpoint-groups')

@Make.inline()
def Certs(self):  _make_delete(self, 'ssl-certificates')

@Make.inline()
def Routers(self): _make_delete(self, 'routers')

@Make.inline()
def FirewallRules(self): _make_delete(self, 'firewall-rules')

@Make.inline()
def Subnets(self): _make_delete(self, 'networks', 'subnets')

@Make.inline()
def Networks(self): _make_delete(self, 'networks')

@Make.inline()
def IPAddresses(self): _make_delete(self, 'addresses')

@Make.inline()
def SecurityPolicies(self): _make_delete(self, 'security-policies')
