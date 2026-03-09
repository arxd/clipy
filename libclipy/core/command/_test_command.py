import pytest
from .dfn import cmd as CLI
from .errors import *
from .param import Param, param_type



@pytest.mark.xfail
def test_bind_cli_missing():
    ''' If all non-hidden arguments are not properly bound by the end of bind_cli then errors are thrown
    '''
    assert(0)



def test_call():
    args = kwargs = None
    @CLI
    def foo(x:int, *_args, **_kwargs):
        nonlocal args, kwargs
        args, kwargs = _args*x, _kwargs
        return 'abc'
    assert(foo(2, 'a','b', d=3) == 'abc')
    assert(args == ('a','b','a','b'))
    assert(kwargs == {'d':3})
    


def test_sub_command():
    @CLI('._testing_cmds', 'libclipy.core.command._testing_cmds')
    def foo(x:int, **kwargs): pass
    assert(repr(foo.bind('9','-x','10','bar-')) == f"foo(10) -> bar-fing()")
    assert(repr(foo.bind('9','-x','10','bar','x')) == f"foo(10) -> bar('x', -)")
    with pytest.raises(UnknownSubCommand) as e:
        foo.bind('-','bax')
    assert('bax' in str(e.value) and 'bar-fing' in str(e.value))
    with pytest.raises(AmbiguousSubCommand) as e:
        foo.bind('-','ba')
    assert('jim' not in str(e.value) and 'baz' in str(e.value))
    with pytest.raises(HelpWanted) as e:
        foo.bind('9', '-h', 'ba')
    assert(str(e.value))



def test_nothing_for_list():
    ''' Don't give a list anything
    '''
    @CLI
    def foo(x:list[int]): pass
    for t in [
        ("foo(-)", ),
        ("foo([3])", '3'),
        ("foo(-)", '-'),
    ]: assert(repr(foo.bind(*t[1:])) == t[0])
    with pytest.raises(MissingArgument):
        foo.bind('-x', '-x', '3')



def test_list_accumulation():
    ''' Repeated values extend lists
    '''
    @CLI
    def foo(x:list[bool]): pass
    assert(repr(foo.bind('T', 'F', 'T', '-x', 'F', 'T', '-x', 'T')) == "foo([True, False, True, False, True, True])")
    with pytest.raises(ParseError) as e:
        foo.bind('-x','y','z')
    assert('2nd' in str(e.value))



def test_skip_keyword():
    ''' --key-word -
    '''
    @CLI
    def foo(*, x:bool, y:int): pass
    foo.bind('-y', '-', '-xx', '-')



def test_keyword_equals():
    ''' --kw=abc
    '''
    @CLI
    def foo(x:bool, *, bob_cob, j): pass
    for t in [
        ("foo(True, bob_cob='-x', j='1 2 3')", '--bob-cob=-x', '-xj=1 2 3'),
    ]: assert(repr(foo.bind(*t[1:])) == t[0])
    


def test_tuple_type():
    '''  x:tuple  tuple[]  tuple[int]  tuple[int*]  tuple[int,str]
    '''
    @CLI
    def foo(a:tuple, b:tuple[int], c:(int,str), d=tuple(), e=(1,True)): pass
    for t in [
        ("foo(('a', 'b', 'c'), (-3, 4, 5), (6, '7'), ('-', '', ' '), (9, True))", 'a,b,c', '-3,4,5', '6,7', '-,, ', '9,y'),
        ("foo(('a',), -, (-3, ' --'), -, -)", 'a', '-', '-0b11, --'),
        ("foo(('-bob', '-cob'), -, -, -, -)", '\\-bob,-cob'),
        ("foo(-, -, (-3, '#'), -, -)", '-c=-3,#'),
    ]: assert(repr(foo.bind(*t[1:])) == t[0])
    with pytest.raises(ParseError) as e:
        foo.bind('-','-','9')
    assert('tuple[int,str]' in str(e.value))
    with pytest.raises(ParseError) as e:
        foo.bind('-','-','9,a,b')
    assert("'9', 'a', 'b'" in str(e.value))



def test_int_type():
    ''' Different int possibilites
    '''
    @CLI
    def foo(a:int, b:list[int]): pass
    with pytest.raises(ParseError):
        foo.bind('-0.0')
    for t in [
        ("foo(-63, -)", '-0x3f'),
        ("foo(0, -)", '\\-0b0'),
        ("foo(0, -)", '-0'),
        ("foo(-, [-1, -2, 3, 4, 5])", '-', '-1','-0x2','3','-b','4','5'),
    ]: assert(repr(foo.bind(*t[1:])) == t[0])



def test_bool_type():
    ''' Bool type is a flag when keyword only, otherwise true false
    '''
    @CLI
    def foo(a:bool, /, b:bool, *, c:bool, d:int): pass
    with pytest.raises(NotBool) as e:
        foo.bind('-dc', '3')
    assert('-dc' in str(e.value) and "'int'" in str(e.value))
    with pytest.raises(ParseError):
        foo.bind('nope')
    for t in [
        ("foo(True, -)", '\\t'),
        ("foo(-, 2, c=3)", '-', '1', '-bccc'),
        ("foo(-, -, c=4, d=5)", '-ccd', '3', '-c', '-d', '5', '-c'),
        ("foo(-, False, c=False)", '-', '1', '-ccc', 'off', '-b','FALSE'),
        ("foo(-, 3)", '-','t', '-bb', 't'),
    ]: assert(repr(foo.bind(*t[1:])) == t[0])




def test_missing_argument():
    ''' You must pass an argument to a kw arg
    '''
    @CLI
    def foo(*, a:bool, b:int, c:list, **kwargs): pass
    with pytest.raises(MissingArgument) as e:
        foo.bind('-ab', '-a')
    assert('-b' in str(e.value))
    assert(repr(foo.bind('-ab', '-0x0', '-a')) == "foo(a=2, b=0)")
    with pytest.raises(MissingArgument):
        foo.bind('-ab', '-0x0', '-b')
    


def test_args_kwargs():
    @CLI
    def foo(a,/,b,*,the_cat__c__kitty, d__dog='woof'): pass
    with pytest.raises(ValueError) as e:
        foo.bind().args_kwargs(h=3)
    assert('reserved' in str(e.value))
    with pytest.raises(MissingArgument) as e:
        foo.bind('-','4').args_kwargs(3)
    assert('--kitty' in str(e.value))
    with pytest.raises(MissingArgument) as e:
        foo.bind('-c','bob').args_kwargs(Param.unset, 4)
    assert("'a'" in str(e.value))
    assert(foo.bind('1','-c','4').args_kwargs(Param.unset, 2, d__dog=Param.unset) == (['1',2], {'the_cat__c__kitty':'4', 'd__dog':'woof'}))
    with pytest.raises(TypeError) as e:
        foo.bind('1','2', '-c', '3').args_kwargs(1,2,3,5)
    assert('4' in str(e.value))
    with pytest.raises(TypeError) as e:
        foo.bind('1','2').args_kwargs(the_cat__c__kitty=3, b=4, a=1)
    assert('unexpected keyword' in str(e.value) and "'a'" in str(e.value))
    assert(foo.bind('-c','x', '-d','-').args_kwargs(1,2,b=3,the_cat__c__kitty=9, d__dog=10) == ([1,3], {'the_cat__c__kitty':'x', 'd__dog':10}))
    @CLI
    def foo(a, *args, **kwargs): pass
    assert(foo.bind('-','b','c').args_kwargs(1,2,3,4,5) == ([1,'b','c'], {}))
    assert(foo.bind('a').args_kwargs(1,2,3,4,5) == (['a',2,3,4,5], {}))



def test_var_pos():
    ''' Extra arguments at the end go to varargs
    '''
    @CLI
    def foo(x, y=3, *rest): pass
    assert(repr(foo.bind('a', '--', '-c', '-d')) == "foo('a', -, '-c', '-d')")
    @CLI
    def foo(x, y, *_rest): pass
    with pytest.raises(ExtraArguments) as e:
        foo.bind('a','b', 'x y z', 't')
    assert("'x y z' t" in str(e.value))



def test_custom_parser():
    ''' You can define your own types
    '''
    @param_type
    def my_parser(self, sval, kw): return sval.upper()
    @CLI
    def foo(x:my_parser, y:list[my_parser]): pass
    assert(repr(foo.bind('abc', 'def', 'ghi')) == "foo('ABC', ['DEF', 'GHI'])")



def test_var_kw():
    ''' Unknown kwargs get added to kwargs
    '''
    @CLI
    def foo(a, /, *, b__bob:bool, **kwargs): pass
    for t in [
        ("foo(-, b__bob=True, a='xyz', bob_cob='99', x='-abc')", '-ba','xyz', '--bob-cob', '99', '-x', '\\-abc'),
    ]: assert(repr(foo.bind(*t[1:])) == t[0])

    @CLI
    def foo(a, /, b__bob_cob:bool, **_kwargs): pass
    with pytest.raises(UnknownKey) as e:
        foo.bind('-ba', '3')
    assert('-b' in str(e.value))
    with pytest.raises(UnknownKey) as e:
        foo.bind('---bob-cob', '9')
    assert('---bob-cob' in str(e.value))



def test_var_kw_coerce():
    ''' Unknown kwargs get added to kwargs
    '''
    @CLI
    def foo(a:int, /, *, b__bob:int, **kwargs): pass
    with pytest.raises(ParseError) as e:
        foo.bind('-b', '3.2')
    assert('-b' in str(e.value))



def test_positional():
    ''' Run out of arguments
    '''
    @CLI
    def foo(a,b=3,/,c:float=None): pass
    with pytest.raises(ParseError) as e:
        foo.bind('-','9.9')
    assert('9.9' in str(e.value))
    for t in [
        ("foo(-, -1, -)", '-','-1'),
        ("foo('0x3f', 63, -)", '0x3f','0x3f'),
        ("foo('', -, -)", '\\'),
        ("foo('--hi', 493, -)", '\\--hi','0755'),
        ("foo(-, 13, -314000000.0)", '-','0b1101','-3.14e8'),
    ]: assert(repr(foo.bind(*t[1:])) == t[0])



def test_positional_list():
    ''' Positional list items are taken until a hyphen ends the list
        x:list[]  x:list[bool]
    '''
    @CLI
    def foo(a:list, b:list[int], c:list[bool]=[1,2,3], d=[1.0]): pass
    for t in [
        ("foo(['a', 'b', 'c'], -, -, -)", 'a','b','c'),
        ("foo(-, [-2, 3], [True], -)", '-','-2','3', '-','T'),
        ("foo(-, -, -, [4.0])", '-','-','-','4'),
    ]: 
        print(t)
        assert(repr(foo.bind(*t[1:])) == t[0])



def test_command_name():
    ''' Command names can only use single underscores, no leading underscores
    '''
    with pytest.raises(InvalidCommandName) as e:
        @CLI
        def bad__(): pass
    assert('double' in str(e.value))
    with pytest.raises(InvalidCommandName):
        @CLI
        def _leading(): pass
    with pytest.raises(InvalidCommandName) as e:
        @CLI
        def _(): pass
    assert('leading' in str(e.value))
    @CLI
    def good_(): pass
    @CLI
    def good_also_(): pass
    @CLI
    def this_is_also_fine(): pass



def test_alias_duplicate():
    ''' Aliases must be unique
    '''
    with pytest.raises(DuplicateArgumentAlias) as e:
        @CLI
        def foo(alias1__bob__c, d__bob): pass
    assert('bob' in str(e.value).lower())



def test_alias_help():
    ''' You can't alias 'h' or 'help'
    '''
    with pytest.raises(DuplicateArgumentAlias) as e:
        @CLI
        def foo(bob__help): pass
    assert('help' in str(e.value).lower())
    with pytest.raises(DuplicateArgumentAlias):
        @CLI
        def foo(help): pass
    with pytest.raises(DuplicateArgumentAlias):
        @CLI
        def foo(bob__h): pass
            


def test_hidden_names():
    ''' Names beginning with underscore are ignored
    '''
    @CLI
    def foo(*, a__b, _c__d, __efg): pass
    assert(set() == ({'a', 'a__b', 'b'} - foo.alias.keys()))
    assert(set() == {'c','_c__d','d','efg','_efg','__efg'} & foo.alias.keys())
    @CLI()
    def foo(_a, b, c, _d, *vargs, e): pass
    assert(repr(foo.bind('1','2','3')) == "foo(-, '1', '2', -, '3')")
    with pytest.raises(MissingArgument) as e:
        foo.bind()()
    assert('-a' not in str(e.value) and '_a' in str(e.value))



def test_alias_underscores():
    ''' Trailing underscores are ignored, inner underscores are dashes '''
    @CLI
    def foo(a___b__c_, d, e_f________g______, j__i): pass
    assert( {'a___b__c_', 'e_f________g______', 'j__i', 'a','b','c','d','e-f','e_f','g','h','i','j','help'} == set(foo.alias.keys()))
