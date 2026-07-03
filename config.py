from libclipy.CLI import ConfigVar, Target

grep_groups = ConfigVar("grep_groups", {'libclipy': r'libclipy/.*'})


@Target.define(default='dev')
def local():
    pass


@Target.define
def stage():
    pass

