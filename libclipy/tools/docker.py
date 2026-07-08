import json, os, base64, hashlib
from .sys_tool import SysTool
from cli import ConfigVar
from libclipy.core.pretty import CLR


class Docker(SysTool):
    sub_commands = ['run', 'pull', 'stop', 'rm', 'logs']
    #version_re = r'^\D* (?P<v0>\d+)\.(?P<v1>\d+)\.\d+.*$'
    version_probe = r'^\D* (?P<v0>\d+)\.(?P<v1>\d+)\.(?P<v2>\d+).*$'
    cmd = ConfigVar('docker_path The path to the docker executable', default='docker')
    version = ConfigVar('docker_version The desired config version for aws', default='28.0')
    
    
    @classmethod
    def install_help_generic(self, print):
        print.ln("Orbstack is recommended on macos. https://orbstack.dev/")


    def _json_list(self, key, *args):
        all = {}
        for line in self(*args, if_0='utf8,,', msg=None).split('\n'):
            if not line: continue
            line = json.loads(line)
            all[line[key]] = line
        return all


    def containers(self):
        return self._json_list('Names', 'container', 'ls', '-a', '--format', 'json')
    

    def volumes(self, search=None):
        cmd = ['volume', 'ls']
        if search: cmd += ['-f', f'name={search}']
        return self._json_list("Name", *cmd, '--format', 'json')
    

    def images(self, search=None):
        args = ['-a'] if search == None else ['-f',f'reference={search}']
        return self._json_list('Repository', 'images', *args, '--format', 'json')


    def ensure_image(self, name, dockerfile, *, remove_old=True):
    # Use the hash of the dockerfile as the tag
        digest = hashlib.sha256(b''.join(line.encode('utf8') for line in dockerfile)).digest()        
        tag = base64.b64encode(digest, altchars=b'_-').decode('utf8').replace('=','')
    # Find existing images
        image = None
        old_images = []
        for img in self.images(f'{name}:*').values():
            if img['Tag'] == tag:
                image = img
            else:
                old_images.append(img['ID'])
    # Delete old images
        if remove_old and old_images:
            Docker()('rmi', *old_images, msg=f"{CLR.y}Removing {len(old_images)} old image(s){CLR.x}")
    # If we don't have an image then create it
        if not image:
            os.environ['DOCKER_BUILDKIT'] = '1'
            name_tag = f'{name}:{tag}'
            cmd = ['build', '-f-', '.', '-t', name_tag]
            platform = os.uname().machine
            if platform != 'arm64': platform = 'amd64'
            cmd += [f'--platform=linux/{platform}']
            self(*cmd, msg=f"Building image: {CLR.y}{name}{CLR.x}", stdin='\n'.join(dockerfile))
            image = self.images(name_tag)[name]
        return image


    def ensure_volume(self, name):
        if not self.volumes(name):
            self('volume', 'create', name, msg=f"Creating persistent volume: {CLR.y}{name!r}{CLR.x}")
        return name
