import pytest

from .config import ConfigVar, UNSET, Target


@pytest.fixture(autouse=True, scope="function")
def cleanup_vars():
    all = Target.all
    ConfigVar.preserve = False
    yield
    Target.all = all


def test_system_dependant_target():
    capture = []
    @Target(system='sys1')
    def a(): capture.append(1)

    @Target(system='sys3, sys2')
    def a(): capture.append(2)

    @Target()
    def a(): capture.append(3)

    assert(list(zip(*a.system_fn))[0] == ('sys1', 'sys3', 'sys2', ''))

    Target.call('a', 'sys1')
    Target.call('a', 'sys2')
    Target.call('a', 'sys3')
    Target.call('a', 'sys4')
    a.apply()
    a.apply('sys2')
    assert(capture == [1,2,2,3,3,2])


def test_calling_nonexist_target_ok():
    capture = []
    @Target()
    def a(): capture.append(1)
    Target.call('z', 'sys')
    assert(capture == [])
        

def test_configvar_constructor_1():
    ''' You can create a variable with only the constructor and a name '''
    foo = ConfigVar('foo')
    assert((foo.name, foo.doc, foo.default) == ('foo','', UNSET))
    assert(foo.v is UNSET)


def test_configvar_constructor_2():
    ''' You can create a variable with a name and description and default value '''
    foo = ConfigVar('foo hello world', default=None)
    assert((foo.name, foo.doc, foo.default) == ('foo','hello world', None))
    assert(foo.v is None)


def test_configvar_constructor_3():
    ''' A name-less configvar is not usable '''
    foo = ConfigVar()
    assert((foo.name, foo.doc, foo.default) == ('', '', UNSET))
    with pytest.raises(AttributeError):
        foo.v = 3


def test_configvar_decorator_1():
    ''' You can create a variable as a decorator, name-only '''
    @ConfigVar()
    def foo(x): return x
    assert((foo.name, foo.doc, foo.default) == ('foo','', UNSET))


def test_configvar_decorator_2():
    ''' The default value can be in the constructor when used as a decorator '''
    @ConfigVar(default=3)
    def foo(x): return x
    assert(foo.default == 3)


def test_configvar_decorator_3():
    ''' The default value in the signature overrides the default value in the constructor, even if it is UNSET '''
    @ConfigVar(default=3)
    def foo(x=UNSET): return x
    assert(foo.default == UNSET)


def test_configvar_decorator_3():
    ''' The name in the constructor overrides the function's name '''
    @ConfigVar('bar')
    def foo(x=3): return x
    assert((foo.name, foo.doc, foo.default) == ('bar','', 3))


def test_configvar_decorator_3():
    ''' function docstring overwrites parameter docstring '''
    @ConfigVar('bar hello')
    def foo(x=3):
        ''' docstring
        '''
        return x
    assert('hello' not in foo.doc)
