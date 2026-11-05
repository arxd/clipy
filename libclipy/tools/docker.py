import json, os, base64, hashlib
from .sys_tool import SysTool
from cli import ConfigVar, project_root
from libclipy.core.pretty import CLR
from libclipy.core.command.cmd import Cmd



class Container():
    ''' A running container
    '''
    def __init__(self, docker, *args):
        self.docker = docker
        self.args = args

    def cmd(self, *args, user=None, **kwargs):
        return self.docker.exec(*['-u', user]*bool(user), self.container_id, *args, **kwargs)

    def cp(self, path_from, path_to):
        _add_hash = lambda x: f'{self.container_id}{x}' if str(x).startswith(':') else x
        self.docker.cp(_add_hash(path_from), _add_hash(path_to)).say().call('null')

    def __enter__(self):
        self.container_id = self.docker.run('-d', *self.args, 'tail','-f','/dev/null').call('utf8').strip()
        return self

    def __exit__(self, *_):
        self.docker.rm('-f', self.container_id).call('null')



class Docker(SysTool):
    sub_commands = ['run', 'rmi', 'volume', 'pull', 'exec', 'stop', 'rm', 'cp', 'tag', 'logs']
    version_probe = r'^\D* (?P<v0>\d+)\.(?P<v1>\d+)\.(?P<v2>\d+).*$'
    cmd = ConfigVar('Docker.cmd The path to the docker executable', default='docker')
    version = ConfigVar('Docker.version The desired config version for aws', default='28.0')
    
    
    @classmethod
    def install_help_macos(self):
        return ["Orbstack is recommended on macos. https://orbstack.dev/"]


    def _json_list(self, key, *args):
        all = {}
        for line in self(*args).call('lines'):
            if not line.strip(): continue
            line = json.loads(line)
            all[key.format(**line)] = line
        return all


    def container(self, *args):
        return Container(self, *args)
    

    def containers(self):
        return self._json_list('{Names}', 'container', 'ls', '-a', '--format', 'json')
    

    def volumes(self, search=None):
        cmd = ['volume', 'ls']
        if search: cmd += ['-f', f'name={search}']
        return self._json_list('{Name}', *cmd, '--format', 'json')
    

    def images(self, search=None):
        args = ['-a'] if search == None else ['-f',f'reference={search}']
        return self._json_list('{Repository}:{Tag}', 'images', *args, '--format', 'json')


    def ensure_image(self, name, dockerfile, *, root='.', secrets={}, build_args={}, remove_old=True):
    # Use the hash of the dockerfile and other inputs as the tag
        hash_input = bytearray(b''.join(line.encode('utf8') for line in dockerfile))
        for s in sorted(secrets): hash_input.extend(s.encode('utf8') + b'\x00' + secrets[s].read_bytes())
        for k in sorted(build_args): hash_input.extend(f'{k}={build_args[k]!r}'.encode('utf8'))
        tag = base64.b64encode(hashlib.sha256(hash_input).digest(), altchars=b'_-').decode('utf8').replace('=','')
    # Find existing images
        image = None
        old_images = []
        for img in self.images(name).values():
            if img['Tag'] == 'latest': continue
            if img['Tag'] == tag:
                image = img
            else:
                old_images.append(img['ID'])
        if image: return img
    # Build it
        name_tag = f'{name}:{tag}'            
        cmd = ['build', '-f-', (project_root/root).resolve()]
        cmd += [x for k,v in secrets.items() for x in ('--secret', f'id={k},src={v}')]
        cmd += [x for k,v in build_args.items() for x in ('--build-arg', f"{k}={v}")]
        cmd += ['-t', name_tag]
        platform = os.uname().machine
        if platform != 'arm64': platform = 'amd64'
        cmd += [f'--platform=linux/{platform}']
        self(*cmd).env(DOCKER_BUILDKIT=1).say(f"Building image: {CLR.y}{name}{CLR.x}").call(stdin='\n'.join(dockerfile))
        image = self.images(name_tag)[name_tag]
        self.tag(image['ID'], f'{name}:latest').say().call()
    # Delete old images
        if remove_old and old_images:
            self.rmi(*old_images).say(f"{CLR.y}Removing {len(old_images)} old image(s){CLR.x}").call()



    def ensure_volume(self, name):
        if self.volumes(name): return True
        self.volume('create', name).say(f"Creating persistent volume: {CLR.y}{name!r}{CLR.x}").call()
