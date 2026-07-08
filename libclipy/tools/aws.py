import json, os
from cli import run, ConfigVar, UsageError
from libclipy.core.pretty import CLR
from .sys_tool import SysTool


class Bucket():
    def __init__(self, aws, bucket):
        self.bucket = bucket
        self.aws = aws

    def download(self, src, dest, *args, **kwargs):
        self.aws.s3('cp', f's3://{self.bucket}/{src}', dest, *args, **kwargs)

    def ls(self, prefix, *args, **kwargs):
        return self.aws.s3api('list-objects-v2', '--delimiter', '/', '--bucket', self.bucket, '--prefix', prefix, *args, if_0='json,,', **kwargs)

    def upload(self, src, dest, *args, **kwargs):
        dest = f's3://{self.bucket}/{dest}'
        self.aws.s3('cp', src, dest, *args, **kwargs)
        return dest



class Aws(SysTool):

    sub_commands = ['s3', 's3api', 'greengrassv2', 'iot']
    version_probe = r'^.*aws-cli/(?P<v0>\d+)\.(?P<v1>\d+)\.(?P<v2>\d+).*$'
    cmd = ConfigVar('aws_path The path to the aws executable', default='aws')
    version = ConfigVar('aws_version The desired config version for aws', default='2.30')
    default_profile = ConfigVar('default_profile Profile name corresponding to profiles in ~/.aws/config used when no profile is given explicitly')


    def __init__(self, profile =None):
        self.profile = profile or self.default_profile.v or None
        self.region, ecode = run(('aws', 'configure','get', 'region'), msg=None, or_else='utf8,,code', env={**os.environ, 'AWS_PROFILE':str(self.profile)})
        if ecode:
            raise UsageError(f"You must add the aws profile {CLR.y}{self.profile}{CLR.x} to ~/.aws/config\n\n  $ aws configure sso")
        self.region = self.region.strip()
        if not self.region:
            raise UsageError(f"No region set in the config.\n``  $ aws configure list``.\n``  $ aws configure sso`` or manually in ``~/.aws/config``.")
    

    @classmethod
    def install_help_generic(self):
        return ['$ curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"',
                '$ unzip awscli-bundle.zip',
                '$ sudo ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws1']


    def prepare_call(self, *cmd, **kwargs):
        if 'env' not in kwargs or not kwargs['env']:
            kwargs['env'] = dict(os.environ)
        kwargs['env']['AWS_PROFILE'] = str(self.profile)
        kwargs['env']['AWS_DEFAULT_OUTPUT'] = 'json'
        return (self.cmd.v, *cmd), kwargs


    def thing_info(self, thing, extra=True):
    # Check for a thing
        args = ['--thing-name', thing]
        info = None if thing[0] == '#' else self.iot('describe-thing', *args, msg=None, if_0='json,,', if_254='null,null,')
        if info != None:
            info = {'arn':info['thingArn'], 'name':info['thingName'], 'id':info['thingId'], 'attrs':info['attributes'], 'version':info['version']}
            if extra: info['groups'] = [g['groupName'] for g in self.iot('list-thing-groups-for-thing', *args, msg=None, if_0='json,,')['thingGroups']]
            return info
    # Check the thing groups
        args = ['--thing-group-name', thing[1:] if thing[0] == '#' else thing]
        info = self.iot('describe-thing-group', *args, msg=None, if_0='json,,', if_254='null,null,')
        if info == None: return None
        info = {'arn':info['thingGroupArn'], 'name':info['thingGroupName'], 'id':info['thingGroupId'], 'attrs':info['thingGroupProperties'], 'version':info['version']}
        if extra: info.update(self.iot('list-things-in-thing-group', *args, '--no-paginate', msg=None, if_0='json,,'))
        return info
    

    def bucket(self, bucket):
        return Bucket(self, bucket)


    def get_deployment(self, target_arn):
        '''Return the components dict of the latest Greengrass deployment for target_arn, or {}.'''
        deployments = self.greengrassv2('list-deployments', '--target-arn', target_arn, if_0='json,,')['deployments']
        if not deployments: return {}
        return self.greengrassv2('get-deployment', '--deployment-id', deployments[0]['deploymentId'], if_0='json,,', msg=None).get('components', {})


    def deploy_components(self, target_arn, components, *, version=None, cfg_merge=None, cfg_reset=None, existing=None, name=None, msg=None):
        '''Merge components into the existing Greengrass deployment for target_arn and create a new deployment.'''
        if isinstance(components, str):
            update = {'merge': json.dumps(cfg_merge)}
            if cfg_reset: update['reset'] = cfg_reset
            components = {components:{'componentVersion':version, 'configurationUpdate': update}}
        existing = self.get_deployment(target_arn) if existing is None else existing
        merged = {**existing, **components}
        cmd = ['create-deployment', '--target-arn', target_arn, '--components', json.dumps(merged)]
        if name: cmd += ['--deployment-name', name]
        return self.greengrassv2(*cmd, if_0='json,,', msg=msg)


    def get_component(self, name):
        cpts = self.greengrassv2('list-components','--query', f"components[?componentName=='{name}']", if_0='json,,', msg=f"Looking for component {name!r}")
        if not cpts: return None
        return cpts[0]
