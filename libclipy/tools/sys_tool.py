from ..core.errors import UsageError


class MissingTool(UsageError):
    def __init__(self, *, tool, msg, need=None, got=None, help=None):
        msg = [f"{CLR.r}{msg}{CLR.x}"]
        if need: msg += [f"{CLR.y}{tool.__mro__[1].__name__}{CLR.x} requires version >= {CLR.m}{need}{CLR.x}"]
        if got:
            msg += [f'Version {CLR.r}{got}{CLR.x} was found.']
        if help:
            if help == True:
                import platform
                if hasattr(tool, 'install_help_generic'): msg += [''] + tool.install_help_generic()
                pfm = 'install_help_' + platform.platform().lower().split('-')[0]
                if hasattr(tool, pfm): msg += [''] + getattr(tool, pfm)()
            else:
                msg += [help] if isinstance(help, str) else help            
        super().__init__(msg)



class VerifiedTool(type):
    ''' This is the meta-class for a SysTool.

    Its primary job is to override __call__ so that we can use the *args to get a singleton, verified, dynamic sub-class of our Tool.

    We only want to perform one existence/version verification probe.
    '''
    _instances = {}

    def __call__(self, *verify_args, **kwargs):
        ''' Called when a tool is instantiated ``Tool(*verify_args, **kwargs)``

        If Tool(*verify_args) is unique then a new subclass of our Tool class will be dynamically created and re-used when those same *verify_args are used again.
        '''
    # The return probed_tool(**kwargs) will recurse to this __call__.
    # Catch that and return an actual object (__init__ needs to be called manually)
        if '__' in self.__name__:
            obj = object.__new__(self)
            obj.__init__(**kwargs)
            return obj
    # Hash *verify_args to make a unique name
        name = f"{self.__name__}__{hex(abs(hash(verify_args)))}"
        try:
            MyVerifiedTool = self._instances[name]
        except KeyError:
            MyVerifiedTool = VerifiedTool(name, (self,), {})
            self._instances[name] = MyVerifiedTool
            MyVerifiedTool.verify(*verify_args)
        return MyVerifiedTool(**kwargs)
    

    def verify(self, version=None):
        ''' This will be called once per `version` to verify the tool's existence and valid version
        '''
        if version is None: version = None if self.version is None else (cfg('version', self) or None)
        if self.version_probe is None:
            assert(version is None), f"A version {version!r} is being specified without a defined version_probe"
        else:
            probe, probe_re = self.version_probe if isinstance(self.version_probe, tuple) else ((self.cmd, '--version'), self.version_probe)
            self.ensure_version(probe, probe_re, version)
    

    def ensure_version(self, probe, probe_re, version):
        ''' Given the `probe` command, does the returned version (matched through `probe_re`) match `version`?
        '''
    # Run the probe command and collect all output
        try:
            got = run(probe, msg=None, if_0='utf8,utf8,')
            assert(got:=(got[0] + got[1]).strip())
        except Exception as e:
            raise MissingTool(tool=self, msg=f"Tool probe failed: {CLR.m}{probe}{CLR.x}", need=version, help=True)
    # Match the tool output with the probe_re regular expression
        try:
            assert(m:=re.match(probe_re, got, re.I | re.MULTILINE))
            got = got[m.start():m.end()]
        except:
            raise MissingTool(tool=self, got=got, msg=f"Probe output doesn't match probe regular expression: {CLR.y}{probe_re}{CLR.x}")
    # If the match result is a string then match against that string
        try:
        # If no version is specified then everything is good
            if not version:
                pass
        # Do a regex string match
            elif 'v' in m.groupdict():
                assert(re.match(version, m['v'])), "Version mismatch"
        # Do a semver match against the matched groups v0, v1, ...
            else:
                for i, v in enumerate(version.split('.')):
                    assert((delta := int(v) - int(m[f'v{i}'])) <= 0), "Minimum version requirement not met"
                    if delta < 0: break
        except Exception as e:
            raise MissingTool(tool=self, msg=str(e), got=got, need=version, help=True)


    def install_help_generic(self):
        ''' Return a list of helpful lines of text that tells the user how to install this command.
        '''
        return [f'Install {self.cmd}']



class SysTool(metaclass=VerifiedTool):
    ''' This represents a system (command-line) tool.

    The tool will be probed for existence (and version) only the first time it is needed.
    Subsequent instantiations (with the same *args) will use the cached instance and not run another probe.

    class MyTool(SysTool): ...
    
    When a unique set of *args is given, as in ``MyTool(*args, food='apple')``, a new subclass is created.

    class MyTool__1.1(MyTool): ...

    That class is then used to create the actual tool instance.

    MyTool__1.1(food='apple')


    Sub-classes should define the following class-properties:

        cmd
            The name of the command as it would be given on the command-line
            
        sub_commands
            A list of direct sub-commands that can be called as methods on this tool

        version
            A ConfigVar so that the user can override the default tool version project-wide.

        version_probe
            A tuple (cmd, probe_regex) or, if the cmd is (cmd, '--version'), just probe_regex

    '''
    init_defaults = {}
    cmd = None
    sub_commands = []
    version = None
    version_probe = None


    def __init__(self, **kwargs):
        kw = dict(type(self).init_defaults)
        if bad:=(kwargs.keys() - kw.keys()): raise ValueError(f"Invalid kwargs {bad}\nAccepted instance kwargs are {kw.keys()}")
        kw.update(kwargs)
        for k,v in kw.items(): setattr(self, k, v)
    

    def __getattr__(self, cmd):
        if cmd not in type(self).sub_commands: raise AttributeError(f"No attribute or subcommand {cmd!r}")
        return partial(self, cmd.replace('_','-'))

    
    def __call__(self, *cmd, exec=False, **kwargs):  
        return (run_exec if exec else run)(self.prepare_call(*cmd), **kwargs)


    def prepare_call(self, *cmd):
        return (type(self).cmd, *cmd)




from functools import partial
import re
from .run import run, exec as run_exec
from ..CLI import CLR, cfg
