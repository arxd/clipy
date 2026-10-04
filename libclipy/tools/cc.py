import re
from collections import namedtuple
from pathlib import Path
from cli import Cmd, ConfigVar, CLR
from .sys_tool import SysTool, MissingTool


class CC(SysTool):
    ''' clang/gcc c compiler
    FIXME: separate parse_errors and parse_deps.  Use the returncode to make sure there is at least one err returned (to reflect the returncode)
    '''
    sub_commands = []
    version_probe = r'^.*(?P<cmd>gcc|clang).*?(?P<v0>\d+)\.(?P<v1>\d+)\.(?P<v2>\d+).*$'
    cmd = ConfigVar('cc_path The path to the compiler executable', default='')
    version = ConfigVar('cc_version The desired c compiler version clang or gcc', default='gcc/15 clang/17')
    
    @classmethod
    def verify(self, version=None):
        defaults = dict([x.split('/') for x in (self.version.v).split(' ')])
        _opt = lambda x: (x[0],defaults[x[0]]) if len(x) == 1 else x
        options = dict([_opt(x.split('/')) for x in (version or self.version.v).split(' ')])
        if '' in options: options = dict(zip(defaults.keys(), [options['']]*len(defaults)))
        err = None
        for cmd in self.cmd.v and [self.cmd.v] or options.keys():
            version = version or self.version.v
            try:
                output = self.run_probe((cmd, '--version'), version)
                stripped = re.sub(r'\([^()]*\)', '', output) # strip () sections
                m, got = self.probe_match(stripped, self.version_probe)
                self.is_gcc = m['cmd'] == 'gcc'
                if m['cmd'] not in options: raise MissingTool(tool=self, got=got, msg=f"Have {m['cmd']!r} but we want {' '.join(options.keys())!r}")
                self.version_check(m, got, options[m['cmd']])
                self.found_cmd = cmd
                break
            except MissingTool as e:
                err = e
            except BaseException as e:
                raise e
        else:
            raise err
    

    def __call__(self, *cmd, **kwargs):
        return Cmd(self.found_cmd, *cmd, **kwargs)


    def compile(self, *, src, obj, include=None, defs=None):
        args = ['-fdiagnostics-color=always' if self.is_gcc else '-fcolor-diagnostics']
        if defs: cmd += [f'-D{k}' if v == 1 else f'-D{k}={v!r}' for k,v in defs.items()]
        if include: cmd += [f'-I{i}' for i in include]
        out = self('-H', '-c', src, '-o', obj, *args).on([0,1],'utf8,utf8').call()
        lines = (out[0] + out[1]).split('\n')
        return self.parse_errors(lines)


    def parse_errors(self, lines):
        msg = re.compile(r'(?P<path>\S.*?):(?P<lno>\d+):(?P<col>\d+):\s*(?P<kind>error|warning):(?P<msg>.*)$')
        dep_done = False
        dep = []
        errs = []
        for line in lines[:-1]:
            if line.startswith('.') and not dep_done:
                try:
                    dep.append(Path(line.split(' ',1)[1]).relative_to(Path('.')))
                except ValueError:
                    pass
                continue
            dep_done = True
            if m:=msg.match(re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)):
                errs.append([m.groupdict(), line])
            else:
                if errs: errs[-1].append(line)
        return dep, errs
    