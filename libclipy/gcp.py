import os, sys, json, paramiko, subprocess, time, socket, tempfile
from cli import print, run, CLR
from config import Config
from pathlib import Path
from google.cloud import compute_v1, service_usage_v1, oslogin_v1
from google.oauth2 import service_account
from google.api_core import exceptions as goog_exc, extended_operation


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]



def port_ready(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        if sock.connect_ex(('127.0.0.1', port)) == 0: return True
    except socket.gaierror: pass
    except socket.error: pass
    finally:
        sock.close()



def port_closed(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)): return True



class SSHSession():
    def __init__(self, iap, **kwargs):
        self.iap = iap
        kwargs.setdefault('sftp', False)
        for k,v in kwargs.items(): setattr(self, k, v)
    

    def __enter__(self):
        username = self.iap.gcp.get_profile().posix_accounts[0].username
        print.ln('SSH connecting as ', CLR.c, username, CLR.x )
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            hostname = 'localhost',
            port = self.iap.port,
            username = username,
            key_filename = str(self.iap.gcp.ssh_key()),
            allow_agent = False,
            look_for_keys = False
        )
        self.sftp = self.ssh.open_sftp() if self.sftp else None
        return self


    def __exit__(self, *args):
        if self.sftp: self.sftp.close()
        self.ssh.close()


    def __call__(self, cmd, *, read=None, silent=False, msg=None, or_else=None, success=[0], progress=None):
        channel = self.ssh.get_transport().open_session()
        if msg != False and not silent:
            print.ln("SSH $ " + cmd if msg == None else msg)
        channel.exec_command(cmd)
        while not channel.exit_status_ready():
            if progress and (p:=progress()):
                channel.close()
                return p
            time.sleep(0.2)
            if read==None and not silent and channel.recv_ready():
                sys.stdout.write(channel.recv(1024).decode("utf8", errors="ignore"))
        if read==None and not silent:
            while txt:=channel.recv(1024).decode("utf8", errors="ignore"): sys.stdout.write(txt)
        stderr = b''
        while (b:=channel.recv_stderr(1024)): stderr += b
        if not silent and stderr:
            print.ln(CLR.r, stderr.decode('utf8'), CLR.x)
        statuscode = channel.recv_exit_status()
        if read:
            stdout = b''
            while (b:=channel.recv(1024)): stdout += b
        if statuscode not in success:
            if or_else != None: return or_else
            if read and not silent: print.ln(stdout.decode('utf8'))
            raise ValueError(f"Command exited with bad status code: {statuscode}", statuscode)
        if not read: return statuscode
        return stdout if read=='bin' else stdout.decode('utf8')



class IAPTunnel():
    def __init__(self, gcp, **kwargs):
        self.gcp = gcp
        kwargs.setdefault('remote_port', 22)
        kwargs.setdefault('project', gcp.cfg.gcp_project)
        kwargs.setdefault('zone', gcp.cfg.gcp_zone)
        for k,v in kwargs.items(): setattr(self, k, v)
        self.port = int(self.port)
        
    
    def __enter__(self):
        if not self.port: self.port = get_free_port()
        if port_closed(self.port):
            assert(self.instance_name), f"Instance name must be specified if no local iap-tunnel is running."
            print.ln('Starting iap-tunnel to ', CLR.m, f'{self.instance_name!r}:{self.remote_port}', CLR.x, ' from ', CLR.c, 'localhost:', self.port, CLR.x)
            cmd = ['gcloud', 'compute', 'start-iap-tunnel', self.instance_name, str(self.remote_port), '--local-host-port',f'localhost:{self.port}', '--project', self.project, '--zone', self.zone]
            self.proc = subprocess.Popen(cmd)#, stderr=subprocess.DEVNULL)
            while port_closed(self.port): time.sleep(0.2)
        else:
            print.ln(f"iap-tunnel already running on localhost:{self.port}")
        return self


    def __exit__(self, *args):
        if hasattr(self, 'proc'):
            self.proc.kill()
            self.proc.communicate()


    def rsync(self, src, dest, *, filter=None, delete=False, auto_install_rsync=True, chown=None):
        profile = self.gcp.get_profile()
        cmd = ['rsync', '-v', '-z', '-rplt', '--rsync-path', 'sudo rsync', '-e', f'ssh -i {self.gcp.ssh_key()} -p {self.port}']
        #if os.path.isdir(str(src)) and not files_from: cmd += ['-r']
        if delete: cmd += ['--delete', '--delete-excluded']
        if filter: cmd += ['--filter', f'. {filter}']
        if chown: cmd += ['--chown',chown]
        cmd += [src, f'{profile.posix_accounts[0].username}@localhost:{dest}']
        try:
            run(cmd, err=False)
        except RuntimeError as e:
            if not auto_install_rsync or e.args[0] != 12: raise e
            print.ln(print.ERR, "Remote does not have rsync")
            with self.ssh() as ssh:
                ssh('sudo apt-get install -y rsync')
            return self.rsync(src, dest, files_from=files_from, auto_install_rsync=False)


    def ssh(self):
        return SSHSession(self)



class GCP():
    def __init__(self):
        self.cfg = Config()
        assert ('gcp_service_account_cred' in self.cfg), f"Can't use GCP from target {self.cfg.target!r}"
        self.cred = service_account.Credentials.from_service_account_file(self.cfg.gcp_service_account_cred, scopes=["https://www.googleapis.com/auth/cloud-platform"])
        self.inst_client = compute_v1.InstancesClient(credentials=self.cred)
        self.ops_client = compute_v1.ZoneOperationsClient(credentials=self.cred)
        self.image_client = compute_v1.ImagesClient(credentials=self.cred)
        self.service_client = service_usage_v1.ServiceUsageClient(credentials=self.cred)
        self.os_client = oslogin_v1.OsLoginServiceClient(credentials=self.cred)


    @staticmethod
    def expand(obj, parent):
        if isinstance(obj, list):
            return [GCP.expand(x, parent) for x in obj]
        if isinstance(obj, dict):
            kls = getattr(parent, obj.pop('_kind')) if '_kind' in obj else None
            obj = {k:GCP.expand(v, parent) for k,v in obj.items()}
            return kls(**obj) if kls else obj
        return obj


    def gcloud(self, *cmd, **kwargs):
        return run(['gcloud', f'--project={self.cfg.gcp_project}', *cmd], **kwargs)


    def _request(self, _cmd, _parent, **kwargs):
        kwargs['zone'] = None if (x:=kwargs.get('zone', '')) == None else x or self.cfg.gcp_zone
        if not kwargs['zone']: del kwargs['zone']
        kwargs['project'] = None if (x:=kwargs.get('project', '')) == None else x or self.cfg.gcp_project
        if not kwargs['project']: del kwargs['project']
        res = _cmd(GCP.expand(kwargs, _parent))
        if isinstance(res, extended_operation.ExtendedOperation):
            res = self.ops_client.wait(project=kwargs['project'], zone=kwargs['zone'], operation=res.name)
        return res


    def get_instance(self, **kwargs):
        try:
            return self._request(self.inst_client.get, compute_v1, _kind='GetInstanceRequest', **kwargs)
        except goog_exc.NotFound:
            return None


    def start_instance(self, **kwargs):
        self._request(self.inst_client.start, compute_v1, _kind='StartInstanceRequest', **kwargs)


    def delete_instance(self, **kwargs):
        self._request(self.inst_client.delete, compute_v1, _kind='DeleteInstanceRequest', **kwargs)


    def stop_instance(self, **kwargs):
        self._request(self.inst_client.stop, compute_v1, _kind='StopInstanceRequest', **kwargs)


    def create_instance(self, zone='', project='', **kwargs):
        inst = dict(_kind='Instance')
        inst.update(**kwargs)
        print.pretty(inst)
        self._request(self.inst_client.insert, compute_v1, _kind='InsertInstanceRequest', zone=zone, project=project, instance_resource = inst)
    
        
    def enable_services(self, services):
        req = dict(_kind='BatchEnableServicesRequest',
            parent = f'projects/{self.cfg.gcp_project}',
            service_ids = list(services),
        )
        print.ln(f"Enabling APIs: {services}")
        self.wait_operation(self.service_client.batch_enable_services(request=GCP.expand(req, service_usage_v1)))


    def get_profile(self):
        if hasattr(self, '_profile'): return self._profile
        self._profile = self._request(self.os_client.get_login_profile, oslogin_v1, _kind='GetLoginProfileRequest', project_id=self.cfg.gcp_project, name=f'users/{self.cred.service_account_email}', zone=None, project=None)
        return self._profile


    def ssh_key(self):
        if hasattr(self,'_ssh_key'): return self._ssh_key
        self._ssh_key = Path("local/iap_ssh_key")
        profile = self.get_profile()  
        if not self._ssh_key.exists():
            print.ftr(f"Generate SSH Key: {self._ssh_key}")
            key = paramiko.RSAKey.generate(2048)
            key.write_private_key_file(self._ssh_key)
            pub = f"{key.get_name()} {key.get_base64()}"
            with open(self._ssh_key.with_suffix('.pub'), 'w') as f: f.write(pub+'\n')
            parent = profile.posix_accounts[0].name.split('/')[:2]
            print.ln(f'import-ssh_public_key: {profile.posix_accounts[0].name!r}  {key.get_name()!r}')
            resp = self._request(self.os_client.import_ssh_public_key, oslogin_v1, _kind='ImportSshPublicKeyRequest', project_id=self.cfg.gcp_project, parent='/'.join(parent), zone=None, project=None, ssh_public_key=dict(key=pub))
        return self._ssh_key


    def iap_tunnel(self, instance_name, **kwargs):
        return IAPTunnel(gcp=self, instance_name=instance_name, **kwargs)

