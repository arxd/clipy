from .command import Command


@Command()
def bar(x, y):
    pass

@Command()
def baz_():
    pass

@Command()
def bar_fing():
    pass

@Command()
def jim():
    pass


def jimbar(prefix):
    return [jim, bar]
