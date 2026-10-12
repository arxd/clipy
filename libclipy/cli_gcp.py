from cli import Command, UsageError, CLR, Cmd, Venv
from libclipy.tools.gcloud import GCloud, get_free_port
from libclipy.core.errors import CmdError


@Command('.cli_gcp')
def gcp():
    ''' Working with Google Cloud
    '''



@Command()
def call(*args):
    ''' Call gcloud with args
    '''
    return GCloud(project_id=True)(*args).exec()



@Command()
def instance(cmd, name, *args):
    ''' Call gcloud compute instances [start | stop | describe | suspend | resume | ...]
    '''
    gcloud = GCloud(project_id=True)
    return gcloud.compute('instances', cmd, name, '--zone', gcloud.instance_to_zone(name), *args).exec()



@Command()
def spawn(name, *, machine__m='e2-micro', image__i='debian-cloud/debian-13', zone__z=None, disk__d='10GB', neg__n=None):
    ''' Spawn a new server instance

    Parameters:
        <name>, --name <name>
            The instance name.
        --machine -m <type> | e2-micro
            The machine type. https://docs.cloud.google.com/compute/docs/general-purpose-machines#e2-standard
        --image -i <name>
            The name of an image or the project/family (e.g. debian-cloud/debian-13, /my-family)
        --disk -d <size> | 10GB
            The size of the disk.
        --zone -z <name> | GCloud.default_zone
            The instance is created in this zone. e.g. us-central1-a
    '''
    gcloud = GCloud(project_id=True)
    if len(img:=image__i.split('/')) == 2:
        image = {'image':gcloud.compute('images', 'describe-from-family', img[1], *('--project', img[0])*bool(img[0]), json=True).call()['selfLink']}
    else:
        image = {'source_machine_image':gcloud.compute('machine-images', 'describe', img[0], json=True).call()['selfLink']}
    if zone__z is None: zone__z = gcloud.zone
    subnet = zone__z.rsplit('-',1)[0]
    print(f'Creating {CLR.c}{name}.{zone__z}.c.{gcloud.project_id}.internal{CLR.x} in subnet {subnet!r}')    
    args = dict(
        zone = zone__z,
        machine_type = machine__m,
        boot_disk_size = disk__d,
        no_boot_disk_auto_delete = None, # Don't delete the instance's boot disk when you delete the VM instance
        subnet = subnet,
        no_can_ip_forward = None, # Can't send/receive packets with an IP address not matching its internal IP
        no_preemptible = None, # Don't create a "spot" instance.
        maintenance_policy = 'MIGRATE', # What to do when the instance needs to move to different physical hardware
        no_address = None, # Don't create a public external IP
        no_service_account = None,
        no_scopes = None, # No legacy OAuth permissions
        metadata = dict(
            enable_oslogin='TRUE', # So we can ssh to the instance
            VmDnsSetting='ZonalOnly', # we get a DNS name {name}.{zone__z}.c.{project_id}.internal
        ),
        **image
    )
    out = dict(args)
    args['metadata'] = ','.join(f"{k.replace('_','-')}={v}" for k, v in args['metadata'].items())
    args = [f"--{k.replace('_','-')}" if v is None else f"--{k.replace('_','-')}={v}" for k,v in args.items()]    
    gcloud.compute('instances', 'create', name, *args).call()
    if neg__n:
        gcloud.compute('network-endpoint-groups', 'update', neg__n, '--zone', zone__z, '--add-endpoint', f'instance={name}').call()
    return out



@Command()
async def infrastructure(*kinds, init=False):
    ''' Show / intialize infrastructure
    
    Parameters:
        kinds | list of 
            One or more of:
                networks networks_subnets security-policies addresses firewall-rules
                routers ssl-certificates network-endpoint-groups forwarding-rules url-maps
                target-http-proxies target-https-proxies backend-services health-checks routers instances
        --init
            Initialize basic infrastructure
    '''
    gcloud = GCloud(project_id=True)
    if init:
        gcloud.services('enable', 'compute.googleapis.com', 'storage.googleapis.com', 'iap.googleapis.com').say().call()
        gcloud.compute('networks', 'create', 'default', '--subnet-mode=custom', '--bgp-routing-mode=global').say().call()
        for i, region in enumerate([gcloud.region, 'us-central1']):
            gcloud.compute('networks', 'subnets', 'create', region, '--network=default','--region', region, f'--range=10.0.{i+1}.0/24').call()
            gcloud.compute('routers', 'create', region, '--network=default', '--region', region).say().call()
            gcloud.compute('routers', 'nats', 'create', region, f'--router={region}','--region', region, '--auto-allocate-nat-external-ips', '--nat-all-subnet-ip-ranges', '--auto-network-tier=PREMIUM').say().call()
        gcloud.compute('firewall-rules', 'create', 'allow-iap-ssh', '--network=default', '--direction=INGRESS','--action=ALLOW', '--rules=tcp:22', '--source-ranges=35.235.240.0/20').say().call()
        gcloud.compute('firewall-rules', 'create', 'allow-internal-cross-region', '--network=default', '--direction=INGRESS', '--action=ALLOW', '--rules=all', '--source-ranges=10.0.1.0/24,10.0.2.0/24').say().call()
        return
    i = {}
    req_services = {'cloudapis.googleapis.com','storage.googleapis.com','monitoring.googleapis.com','serviceusage.googleapis.com','cloudresourcemanager.googleapis.com','servicemanagement.googleapis.com','cloudtrace.googleapis.com', 'bigquery.googleapis.com', 'storage-component.googleapis.com', 'datastore.googleapis.com', 'sql-component.googleapis.com', 'logging.googleapis.com','storage-api.googleapis.com'}
    if not kinds or 'services' in kinds:
        i['services'] = [s['config']['name'] for s in gcloud.services('list', '--enabled', json=True).say().call() if s['config']['name'] not in req_services]
    kinds = [k for k in (kinds or ['networks', 'networks_subnets', 'security-policies', 'addresses', 'firewall-rules', 'routers', 'ssl-certificates', 'network-endpoint-groups', 'forwarding-rules', 'url-maps', 'target-http-proxies', 'target-https-proxies', 'backend-services', 'health-checks', 'instances']) if k not in ['services']]
    for k in kinds:
        i[k] = gcloud.compute(*k.split('_'), 'list', json=True).say().call_async()
    import asyncio
    group = asyncio.gather(*[i[k] for k in kinds])
    try:
        for k, v in zip(kinds, await group):
            i[k] = {s['name']:s for s in v}
    finally:
        group.cancel()
        await group
    return i



@Command()
async def images(image=None, *, status__s=None, create__c=None, family__f=None):
    ''' Show/Create/Remove disks and images.

    Parameters:
        <name>, --image <name>
            Image to create/remove/deprecate.
            If no image is given then list all images.
        --status -s <str>
            Change the image's status:
                ``delete``    | Delete the image
                ``deprecated``| Mark the image as deprecated
                ``deleted``   | Mark the image as deleted (don't actually delete it)
                ``obsolete``  | Mark the image as obsolete
                ``active``    | Move a deprecated image back to active status.
        --create -c <instance>
            Create the image from the given instance.
            The instance will be stopped first
        --family -f <name>
            Create the image as the most recent image in this family.
    '''
    gcloud = GCloud(project_id=True)
    from cli import name
    if create__c:
        zone = gcloud.instance_to_zone(create__c)
        print(f"Creating {image!r} from {zone}/{create__c}")
        inst=gcloud.compute('instances', 'describe', create__c, '--zone', zone, json=True).call()
        status = inst['status']
        source_disk = [d['source'] for d in inst['disks'] if d['boot']][0]
        if status == 'RUNNING':
            if input(f"Stop the instance? [y/N]") != 'y': raise UsageError("Aborting")
            gcloud.compute('instances', 'stop', create__c, '--zone', zone).say().call()
            status=gcloud.compute('instances', 'describe', create__c, '--zone', zone, '--format=value(status)').call('utf8').strip()
        if status != 'TERMINATED': raise UsageError(f"The instance is not in a valid TERMINATED state: {status!r}")
        print(f"Creating the image: {image!r}")
        return gcloud.compute('images', 'create', image, *('--family', family__f)*bool(family__f), '--source-disk', source_disk).say().call()

    
    if not image:
        imgs, disks = await Cmd.all(
            gcloud.compute('images', 'list', '--no-standard-images', '--show-deprecated', json=True).call_async(), 
            gcloud.compute('disks', 'list', json=True).call_async(),
        )
        return {
            'disks':{disk['zone'].rsplit('/',1)[1]+'/'+disk['name']:{k:v for k,v in disk.items() if k in ('sizeGb', 'sourceImage', 'status', 'creationTimestamp')}|{'users':[(parts:=d.split('/'))[-3]+'/'+parts[-1] for d in disk.get('users',[])] } for disk in disks},
            'images':{img['name']:{k:v for k,v in img.items() if k in ('family', 'diskSizeGb', 'creationTimestamp', 'status')}|{'dep_status':img.get('deprecated',{'state':'ACTIVE'})['state']} for img in imgs},
        }
    try:
        img = gcloud.compute('images', 'describe', image, json=True).call()
    except CmdError:
        img = gcloud.compute('images', 'describe-from-family', image, json=True).call()
    if status__s == 'delete':
        gcloud.compute('images', 'delete', img['selfLink']).say().call()
    elif status__s in ('deprecated', 'active'):
        gcloud.compute('images', 'deprecate', '--state', status__s, img['selfLink']).say().call()
    elif status__s: raise UsageError(f"Illegal status {status__s!r}.  It must be one of: delete, deprecated, active, deleted, obsoleteACTIVE, DELETED, DEPRECATED, OBSOLETE")
    else: return img



@Command()
def iap(name, *, port__p=0, remote_port__r=22):
    ''' Start an iap tunnel to instance

    Parameters:
        <name>, --name <name>
            The instance name to connect to
        --remote-port -r <port>
            The remote port to proxy to.  Default is ssh port 22.
        --port -p <port> | 0
            The localhost port to open.
    '''
    return GCloud(project_id=True).iap(vm_name=name, port=port__p, remote_port=remote_port__r).cmd.say().exec()    



@Venv('cli::main', req="paramiko")
@Command()
def ssh(name=None, *, port__p=0):
    ''' Connect to an instance through an iap tunnel.

    If the tunnel is not open then it will be opened.
    If you know the tunnel is already open then you can omit `name`.

    Parameters:
        <name>, --name <name>
            Open an iap tunnel to this instance.
            Exclude this if connecting to an already open tunnel with --port.
        --port -p <port>
            The localhost port to the open tunnel.
            Exclude this if giving an instance name.
    '''
    gcloud = GCloud(project_id=True)
    with gcloud.iap(vm_name=name, port=port__p, remote_port=22) as iap:
        cmd = Cmd('ssh', '-i', gcloud.ssh_key, '-p', iap.port)
        cmd = cmd('-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null')
        cmd.env(LANG='C', LC_ALL='C')
        cmd(f'{gcloud.username}@localhost').say().call()



@Command()
def roles(user__u=''):
    ''' Show users/roles

    Parameters:
        <str>, --user -u <str>
            Filter by username (default is to show all users)
    '''
    gcloud = GCloud(project_id=True)
    users = {}
    for b in gcloud.projects('get-iam-policy', gcloud.project_id, json=True).say().call()['bindings']:
        for usr in b['members']:
            if user__u not in usr: continue
            users.setdefault(usr, [])
            users[usr].append(b['role'][len('roles/'):])
    return users



@Venv(ssh)
@Command()
def setup(name=None, *, system='cloud', port__p=0, target__t='prod', deploy=False, start=-1, stop=0):
    ''' Setup an instance so that when it boots up it runs `./cli.py run`

    Parameters:
        <name>, --name <name>
            Setup this instance.  Optional if there is already an iap tunnel open and you pass `--port -p`.
        --port -p <port>
            The localhost port that the iap tunnel is on (or will be on).
        --system <name>
            The remote clipy will run with CLIPY_SYSTEM=<name>
        --target -t <name>
            The target that the system will run under
        --deploy
            Set start to be the beginning of the code copy action
        --start <int>
            Start running setup commands starting at this index
        --stop <int>
            Run all setup commands until this one and then stop.
    '''
    from libclipy.tools.git import Git
    from libclipy.core.errors import CmdError
    from cli import env_prefix
    if deploy:
        from .cli_lifecycle import SetupJournal
        start = SetupJournal.deploy_start
    gcloud = GCloud(project_id=True)
    with gcloud.ssh(vm_name=name, port=port__p) as ssh:
    # First check to see what the setup status is on this machine
        try:
            ssh.cmd('uv --version').call()
        except CmdError:
            ssh.cmd('sudo groupadd -f -r app').say().call()
            _write_file(ssh, '/usr/local/bin/oslogin_auto_app_group',
                "#!/usr/bin/env python3",
                "import os, sys, grp, subprocess",
                "if not (user:=os.environ.get('PAM_USER')) or user == 'root': sys.exit(0)",
                "user_in_group = user in grp.getgrnam('app').gr_mem",
                "if os.path.isfile(os.path.join('/var/google-sudoers.d', user)):",
                "    if not user_in_group: subprocess.run(['/usr/sbin/usermod','-a','-G','app',user])",
                "elif user_in_group: subprocess.run(['/usr/bin/gpasswd','-d',user,'app'])",
                chmod = '755',
            )
            try:
                ssh.cmd('grep oslogin_auto_app_group /etc/pam.d/sshd').call()
            except CmdError:
                # Add the current user so they don't have to re-login to be in the app group
                ssh.cmd(f'sudo -E PAM_USER=$USER oslogin_auto_app_group').say().call()
                _write_file(ssh, '/etc/pam.d/sshd', '','','session optional pam_exec.so /usr/local/bin/oslogin_auto_app_group', append=True)
            ssh.cmd('sudo apt-get install -y rsync').say().call()
            ssh.cmd('sudo mkdir -p /var/opt/uv/python /var/opt/uv/tools').say().call()
            ssh.cmd('sudo chown -R root:app /var/opt/uv').call()
            ssh.cmd('sudo chmod -R 775 /var/opt/uv').call()
            ssh.cmd('sudo find /var/opt/uv -type d -exec chmod g+s {} +').call() # created files stay owned by the 'app' group
            ssh.cmd('curl -LsSf https://astral.sh/uv/install.sh | sudo UV_INSTALL_DIR="/usr/local/bin" INSTALLER_NO_MODIFY_PATH=1 sh').say().call()
            ssh.cmd('sudo mv /usr/local/bin/uv /usr/local/bin/_uv').say().call()
            _write_file(ssh, '/usr/local/bin/uv', '#!/bin/sh', 'export UV_TOOL_DIR="/var/opt/uv/tools"', 'export UV_PYTHON_INSTALL_DIR="/var/opt/uv/python"', 'exec /usr/local/bin/_uv "$@"', chmod='755')
        ssh.iap.rsync().sync('app', '!local/***', *Git().ls())
        ssh.cmd(f'app/cli.py -t {target__t} setup --stop {stop} --start {start} --git-commit {Git().head_commit()}').env(PYTHONUNBUFFERED=1, **{f'{env_prefix}SYSTEM': system}).say().call(pty=True)


def _write_file(ssh, path, *lines, chmod='644', append=False):
    lines = '\n'.join(lines)
    ssh.cmd(f"sudo tee{' -a'*append} {path} > /dev/null << 'EOF'\n{lines}\nEOF\n").say().call()
    if chmod is not None: ssh.cmd(f'sudo chmod {chmod} {path}').say().call()
