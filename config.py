from libclipy import Target, ConfigVar

verbose = ConfigVar("verbose The verbosity level. 0 is normal, positive is more verbose, negative less verbose", 0)

bob = ConfigVar("bob This is a nice guy", "yup")
cob = ConfigVar("cob")

@Target.define(default='dev')
def local():
    print("Configure local")
    verbose(3)

@Target.define
def prod():
    print("Configure prod")
