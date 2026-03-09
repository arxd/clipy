from .dfn import cmd


@cmd()
def bar(x, y):
    pass

@cmd()
def baz_():
    pass

@cmd
def bar_fing():
    pass

@cmd
def jim():
    pass


def jimbar(prefix):
    return [jim, bar]
