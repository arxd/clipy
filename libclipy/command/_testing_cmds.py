from .dfn import CLI


@CLI()
def bar(x, y):
    pass

@CLI()
def baz_():
    pass

@CLI
def bar_fing():
    pass

@CLI
def jim():
    pass


def jimbar(prefix):
    return [jim, bar]
