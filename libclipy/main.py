import libclipy as CLI


@CLI.cmd
def config_():
    a, b = CLI.cfg('bob cob')
    c = CLI.cfg('target', CLI)
    print(a,b,c)
    for v in CLI.env:
        print(v)



@CLI.cmd(config_, '.docs', 'libclipy.test_cli', need=CLI.pip('PyYAML'))
def main(*, target__t=None, verbose__v=False):
    ''' The main program

    Parameters:
        --target <target>, -t <target>
            Set the target, overriding the environment variable.
        --verbose, -v
            Set the output to be more verbose.
            Use this flag more than once ``-vvv`` to become more and more verbose.
    '''
    if target__t is not None: CLI.env.target = target__t
        