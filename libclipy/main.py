from libclipy import CLI, pip


@CLI
def bob():
    print("HI bob")



@CLI(bob, '.docs', 'libclipy.test_cli', need=pip('PyYAML'))
def main():
    ''' The main program
    '''
    