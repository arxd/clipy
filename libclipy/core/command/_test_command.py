import pytest, asyncio
from .command import Command
from .errors import *
from .param import Param, ParamType


def see_kw(kwargs):
    return ' '.join(f'{k}={kwargs[k]}' for k in sorted(kwargs))



@pytest.mark.xfail
def test_bind_cli_missing():
    ''' If all non-hidden arguments are not properly bound by the end of bind_cli then errors are thrown
    '''
    assert(0)


@pytest.mark.xfail
def test_blank_sub():
    ''' Try to get <blank> subcommand to throw
    '''
    assert(0)



@Command()
async def async_fn(x:int):
    return f"{x}"

def test_async_fn():
    assert(async_fn(3) == '3')



@Command()
def call_(x:int, *_args, _sub_cmd, **_kwargs):
    return f"{x} {_sub_cmd} {_args} {_kwargs}"

def test_call():
    assert(call_(2, 'a','b', d=3, x=4) == "4 None ('a', 'b') {'d': 3}")




@Command('._testing_cmds')
def sub_command(x:int, **kwargs):
    pass

def test_sub_command():
    assert(repr(sub_command.instance().bind('9','-x','10','bar-')) == f"sub-command(10) -> bar-fing()")
    assert(repr(sub_command.instance().bind('9','-x','10','bar','x')) == f"sub-command(10) -> bar('x', -)")
    with pytest.raises(UnknownSubCommand) as e:
        sub_command.instance().bind('-','bax')
    assert('bax' in str(e.value) and 'bar-fing' in str(e.value))
    with pytest.raises(AmbiguousSubCommand) as e:
        sub_command.instance().bind('-','ba')
    assert('jim' not in str(e.value) and 'baz' in str(e.value))
    with pytest.raises(HelpWanted) as e:
        sub_command.instance().bind('9', '-h', 'ba')
    assert(str(e.value))




@Command()
def nothing_for_list(x:list[int]):
    pass

def test_nothing_for_list():
    ''' Don't give a list anything
    '''
    
    for t in [
        ("nothing-for-list(-)", ),
        ("nothing-for-list([3])", '3'),
        ("nothing-for-list(-)", '-'),
    ]: assert(repr(nothing_for_list.instance().bind(*t[1:])) == t[0])
    with pytest.raises(MissingArgument):
        nothing_for_list.instance().bind('-x', '-x', '3')




@Command()
def list_accumulation(x:list[bool]):
    pass

def test_list_accumulation():
    ''' Repeated values extend lists
    '''
    assert(repr(list_accumulation.instance().bind('T', 'F', 'T', '-x', 'F', 'T', '-x', 'T')) == "list-accumulation([True, False, True, False, True, True])")
    with pytest.raises(ParseError) as e:
        list_accumulation.instance().bind('-x','y','z')
    assert('2nd' in str(e.value))




@Command()
def skip_keyword(*args, x:bool, y:int):
    pass

def test_skip_keyword():
    ''' --key-word -
    '''
    assert(repr(skip_keyword.instance().bind('-y', '-', '-xx', '-', 'false')) == "skip-keyword('false', y=-, x=True)")




@Command()
def keyword_equals(x:bool, *, bob_cob, j):
    pass

def test_keyword_equals():
    ''' --kw=abc
    '''
    for t in [
        ("keyword-equals(True, bob_cob='-x', j='1 2 3')", '--bob-cob=-x', '-xj=1 2 3'),
    ]: assert(repr(keyword_equals.instance().bind(*t[1:])) == t[0])




@Command()
def tuple_type(a:tuple, b:tuple[int], c:(int,str), d=tuple(), e=(1,True)):
    pass

def test_tuple_type():
    '''  x:tuple  tuple[]  tuple[int]  tuple[int*]  tuple[int,str]
    '''
    for t in [
        ("tuple-type(('a', 'b', 'c'), (-3, 4, 5), (6, '7'), ('-', '', ' '), (9, True))", 'a,b,c', '-3,4,5', '6,7', '-,, ', '9,y'),
        ("tuple-type(('a',), -, (-3, ' --'), -, -)", 'a', '-', '-0b11, --'),
        ("tuple-type(('-bob', '-cob'), -, -, -, -)", '\\-bob,-cob'),
        ("tuple-type(-, -, (-3, '#'), -, -)", '-c=-3,#'),
    ]: assert(repr(tuple_type.instance().bind(*t[1:])) == t[0])
    with pytest.raises(ParseError) as e:
        tuple_type.instance().bind('-','-','9')
    assert('tuple[int,str]' in str(e.value))
    with pytest.raises(ParseError) as e:
        tuple_type.instance().bind('-','-','9,a,b')
    assert("'9', 'a', 'b'" in str(e.value))




@Command()
def int_type(a:int, b:list[int]):
    pass

def test_int_type():
    ''' Different int possibilites
    '''
    with pytest.raises(ParseError):
        int_type.instance().bind('-0.0')
    for t in [
        ("int-type(-63, -)", '-0x3f'),
        ("int-type(0, -)", '\\-0b0'),
        ("int-type(0, -)", '-0'),
        ("int-type(-, [-1, -2, 3, 4, 5])", '-', '-1','-0x2','3','-b','4','5'),
    ]: assert(repr(int_type.instance().bind(*t[1:])) == t[0])




@Command()
def bool_type(a:bool, /, b:bool, *args, c:bool, d:int):
    pass

def test_bool_type():
    ''' Bool type is a flag when keyword only, otherwise true false
    '''
    with pytest.raises(NotBool) as e:
        bool_type.instance().bind('-dc')
    assert('-dc' in str(e.value) and "'int'" in str(e.value))
    with pytest.raises(ParseError):
        bool_type.instance().bind('nope')
    for t in [
        ("bool-type(False, -)", 'disable'),
        ("bool-type(True, True, 't')", '1', '-b', '\\t','t'),
        ("bool-type(-, 11, c=3)", '-', '10', '-bccc'),
        ("bool-type(-, -, c=4, d=5)", '-ccd', '3', '-c', '-d', '5', '-c'),
        ("bool-type(-, -, c=False)", '-ccc', '0'),
        ("bool-type(-, -, 'cmd', c=5)", '-ccc', '3', 'cmd'),
        ("bool-type(-, 2, 'FALSE', c=False)", '-', '1', '-ccc', '0', '-b','FALSE'),
        ("bool-type(-, 3, 't')", '-','t', '-bb', 't'),
        ("bool-type(-, False)", '-b', '\\FALSE')
    ]: assert(repr(bool_type.instance().bind(*t[1:])) == t[0])




@Command()
def bool_kw(*args, c:bool):
    pass

def test_bool_kw():
    ''' When bool is used as a kw it only accepts 1/0 as an argument and otherwise defaults to True.
    This is so that there are not conflicts with the next command name
    '''
    for v in ['t', 'True', 'False', 'Off', 'no', 'disable']:
        assert(repr(bool_kw.instance().bind('-c', v)) == f"bool-kw({v!r}, c=True)"), v
    assert(repr(bool_kw.instance().bind('-c', '3')) == f"bool-kw(c=3)")
    assert(repr(bool_kw.instance().bind('-cc', '0')) == f"bool-kw(c=False)")
    for v in ['#','\\bad']:
        with pytest.raises(ParseError):
            bool_kw.instance().bind('-c', v)




@Command()
def missing_argument(*, a:bool, b:int, c:list, **kwargs):
    pass

def test_missing_argument():
    ''' You must pass an argument to a kw arg
    '''
    with pytest.raises(MissingArgument) as e:
        missing_argument.instance().bind('-ab', '-a')
    assert('-b' in str(e.value))
    assert(repr(missing_argument.instance().bind('-ab', '-0x0', '-a')) == "missing-argument(a=2, b=0)")
    with pytest.raises(MissingArgument):
        missing_argument.instance().bind('-ab', '-0x0', '-b')
    



@Command()
def args_kwargs(a,/,b,*,the_cat__c__kitty, d__dog='woof'):
    pass

def test_args_kwargs():
    with pytest.raises(ValueError) as e:
        args_kwargs.instance().bind().args_kwargs(h=3)
    assert('reserved' in str(e.value))
    with pytest.raises(MissingArgument) as e:
        args_kwargs.instance().bind('-','4').args_kwargs(3)
    assert('--kitty' in str(e.value))
    with pytest.raises(MissingArgument) as e:
        args_kwargs.instance().bind('-c','bob').args_kwargs(Param.unset, 4)
    assert("'a'" in str(e.value))
    assert(args_kwargs.instance().bind('1','-c','4').args_kwargs(Param.unset, 2, d__dog=Param.unset) == (['1',2], {'the_cat__c__kitty':'4', 'd__dog':'woof'}))
    with pytest.raises(TypeError) as e:
        args_kwargs.instance().bind('1','2', '-c', '3').args_kwargs(1,2,3,5)
    assert('4' in str(e.value))
    with pytest.raises(TypeError) as e:
        args_kwargs.instance().bind('1','2').args_kwargs(the_cat__c__kitty=3, b=4, a=1)
    assert('unexpected keyword' in str(e.value) and "'a'" in str(e.value))
    assert(args_kwargs.instance().bind('-c','x', '-d','-').args_kwargs(1,2,b=3,the_cat__c__kitty=9, d__dog=10) == ([1,3], {'the_cat__c__kitty':'x', 'd__dog':10}))




@Command()
def args_kwargs2(a, *args, **kwargs):
    pass

def test_args_kwargs2():
    assert(args_kwargs2.instance().bind('-','b','c').args_kwargs(1,2,3,4,5) == ([1,'b','c'], {}))
    assert(args_kwargs2.instance().bind('a').args_kwargs(1,2,3,4,5) == (['a',2,3,4,5], {}))



@Command()
def var_pos(x, y=3, *rest):
    pass

def test_var_pos():
    ''' Extra arguments at the end go to varargs
    '''
    assert(repr(var_pos.instance().bind('a', '--', '-c', '-d')) == "var-pos('a', -, '-c', '-d')")
    
 


@Command()
def var_pos2(x, y, *_rest):
    pass

def test_var_pos2():
    with pytest.raises(ExtraArguments) as e:
        var_pos2.instance().bind('a','b', 'x y z', 't')
    assert("'x y z' t" in str(e.value))




@ParamType()
def my_parser(self, sval, kw):
    return sval.upper()

@Command()
def custom_parser(x:my_parser, y:list[my_parser]):
    pass

def test_custom_parser():
    ''' You can define your own types
    '''
    assert(repr(custom_parser.instance().bind('abc', 'def', 'ghi')) == "custom-parser('ABC', ['DEF', 'GHI'])")




@Command()
def var_kw_public(a, /, e, *, b__bob:bool, **kwargs):
    return f'{a} {e} {b__bob} {see_kw(kwargs)}'


def test_var_kw_a():
    ''' Unknown bound kwargs take precedence over programmatic kwargs '''
    assert(var_kw_public.instance().bind('-m','0')(1, 2, b__bob=3, m=4, xtra=5) == '1 2 3 m=0 xtra=5')


def test_var_kw_b():
    ''' It is possible to have a kwarg set with the same name as a positional-only parameter '''
    assert(var_kw_public.instance().bind('0','1','-b','-m','8')(a=10, e=30, m=40, b__bob=20) == '0 1 True a=10 m=8')
    assert(var_kw_public.instance().bind('-ba','0')(1,2) == '1 2 True a=0')


@Command()
def var_kw_private(a, /, b__bob_cob:bool, **_kwargs):
    return f'{a} {b__bob_cob} {see_kw(_kwargs)}'


def test_var_kw_c():
    ''' You can't bind unknown keyword parameters to a private var_kw '''
    with pytest.raises(UnknownKey) as e:
        var_kw_private.instance().bind('-ba', '3')
    assert('-b' in str(e.value))
    with pytest.raises(UnknownKey) as e:
        var_kw_private.instance().bind('---bob-cob', '9')
    assert('---bob-cob' in str(e.value))


def test_var_kw_d():
    ''' You can pass keyword parameters to private var_kw programmatically '''
    assert(var_kw_private.instance().bind('1','-bb')(b=4, z=9) == "1 2 b=4 z=9")




@Command()
def var_kw_coerce(a:int, /, *, b__bob:int, **kwargs):
    pass

def test_var_kw_coerce():
    ''' Unknown kwargs get added to kwargs
    '''
    with pytest.raises(ParseError) as e:
        var_kw_coerce.instance().bind('-b', '3.2')
    assert('-b' in str(e.value))




@Command()
def positional_(a,b=3,/,c:float=None):
    pass

def test_positional():
    ''' Run out of arguments
    '''
    with pytest.raises(ParseError) as e:
        positional_.instance().bind('-','9.9')
    assert('9.9' in str(e.value))
    for t in [
        ("positional(-, -1, -)", '-','-1'),
        ("positional('0x3f', 63, -)", '0x3f','0x3f'),
        ("positional('', -, -)", '\\'),
        ("positional('--hi', 493, -)", '\\--hi','0755'),
        ("positional(-, 13, -314000000.0)", '-','0b1101','-3.14e8'),
    ]: assert(repr(positional_.instance().bind(*t[1:])) == t[0])




@Command()
def positional_list(a:list, b:list[int], c:list[bool]=[1,2,3], d=[1.0]):
    pass

def test_positional_list():
    ''' Positional list items are taken until a hyphen ends the list
        x:list[]  x:list[bool]
    '''
    for t in [
        ("positional-list(['a', 'b', 'c'], -, -, -)", 'a','b','c'),
        ("positional-list(-, [-2, 3], [True], -)", '-','-2','3', '-','T'),
        ("positional-list(-, -, -, [4.0])", '-','-','-','4'),
    ]: 
        print(t)
        assert(repr(positional_list.instance().bind(*t[1:])) == t[0])




def test_command_name():
    ''' Command names can only use single underscores, no leading underscores
    '''
    with pytest.raises(InvalidCommandName) as e:
        @Command()
        def bad__(): pass
    assert('double' in str(e.value))
    with pytest.raises(InvalidCommandName):
        @Command()
        def _leading(): pass
    with pytest.raises(InvalidCommandName) as e:
        @Command()
        def _(): pass
    assert('leading' in str(e.value))
    @Command()
    def good_(): pass
    @Command()
    def good_also_(): pass
    @Command()
    def this_is_also_fine(): pass




def test_alias_duplicate():
    ''' Aliases must be unique
    '''
    with pytest.raises(DuplicateArgumentAlias) as e:
        @Command()
        def foo(alias1__bob__c, d__bob): pass
    assert('bob' in str(e.value).lower())




def test_alias_help():
    ''' You can't alias 'h' or 'help'
    '''
    with pytest.raises(DuplicateArgumentAlias) as e:
        @Command()
        def foo(bob__help): pass
    assert('help' in str(e.value).lower())
    with pytest.raises(DuplicateArgumentAlias):
        @Command()
        def foo(help): pass
    with pytest.raises(DuplicateArgumentAlias):
        @Command()
        def foo(bob__h): pass
            



@Command()
def hidden_names(*, a__b, _c__d, __efg):
    pass

def test_hidden_names():
    ''' Names beginning with underscore are ignored
    '''
    assert(set() == ({'a', 'a__b', 'b'} - hidden_names.instance().alias.keys()))
    assert(set() == {'c','_c__d','d','efg','_efg','__efg'} & hidden_names.instance().alias.keys())


@Command()
def hidden_names2(_a, b, c, _d, *vargs, e):
    pass

def test_hidden_names2():
    assert(repr(hidden_names2.instance().bind('1','2','3')) == "hidden-names2(-, '1', '2', -, '3')")
    with pytest.raises(MissingArgument) as e:
        hidden_names2.instance().bind('1','2','-e','3').args_kwargs(4)
    assert('-d' not in str(e.value) and '_d' in str(e.value))

@pytest.mark.xfail
def test_hidden_names_c():
    ''' A hidden positional parameter can be set from __call__(x) '''
    assert(0)


@Command()
def alias_underscores(a___b__c_, d, e_f________g______, j__i):
    pass

def test_alias_underscores():
    ''' Trailing underscores are ignored, inner underscores are dashes '''
    assert( {'a___b__c_', 'e_f________g______', 'j__i', 'a','b','c','d','e-f','e_f','g','h','i','j','help'} == set(alias_underscores.instance().alias.keys()))




@Command()
def upper_(*, value, _sub_cmd):
    return str(value).upper()

@Command(upper_)
def implicit_generator_cmd(loops:int):
    for i in range(loops):
        yield {'value':['zero','one','two'][i]}

@Command(upper_)
async def implicit_generator_async_cmd(loops:int):
    for i in range(loops):
        await asyncio.sleep(0)
        yield {'value':['zero','one','two'][i]}


def test_implicit_generator_mid_break():
    ''' Break in the middle of iteration
    '''
    for x in implicit_generator_cmd.instance().bind('2','upper').each():
        break
    assert(x == 'ZERO')
    assert(list(implicit_generator_cmd.instance().bind('2','upper').each()) == ['ZERO','ONE'])


def test_implicit_generator_async_mid_break():
    ''' Break in the middle of iteration (async)
    '''
    for x in implicit_generator_async_cmd.instance().bind('2','upper').each():
        break
    assert(x == 'ZERO')
    assert(list(implicit_generator_cmd.instance().bind('2','upper').each()) == ['ZERO','ONE'])
 

def test_implicit_generator_raise():
    ''' A generator can raise an exception '''
    with pytest.raises(IndexError) as e:
        all = []
        for x in implicit_generator_cmd.instance().bind('4','upper').each():
            all.append(x)
    assert(hasattr(e.value, 'traceback_text'))


def test_implicit_generator_async_raise():
    ''' A generator can raise an exception (async) '''
    with pytest.raises(IndexError) as e:
        all = []
        for x in implicit_generator_async_cmd.instance().bind('4','upper').each():
            all.append(x)
    assert(hasattr(e.value, 'traceback_text'))


def test_implicit_generator_call():
    ''' Calling a generator can return zero or more results '''
    assert(implicit_generator_cmd.instance().bind('0','upper')() == Command.no_return)
    assert(implicit_generator_cmd.instance().bind('1','upper')() == 'ZERO')
    assert(implicit_generator_cmd.instance().bind('2','upper')() == ('ZERO','ONE'))


def test_implicit_generator_async_call():
    ''' Calling a generator can return zero or more results (async)'''
    assert(implicit_generator_async_cmd.instance().bind('0','upper')() == Command.no_return)
    assert(implicit_generator_async_cmd.instance().bind('1','upper')() == 'ZERO')
    assert(implicit_generator_async_cmd.instance().bind('2','upper')() == ('ZERO','ONE'))



@Command(upper_)
def explicit_generator_cmd(loops:int, *, _sub_cmd):
    yield from [_sub_cmd(value=['zero','one','two'][i]) for i in range(loops)]
    yield 'done'


def test_explicit_generator_call():
    ''' Explicit generators work the same as implicit generators
    '''
    assert(explicit_generator_cmd.instance().bind('2', 'upper')() == ('ZERO', 'ONE', 'done'))


# ==========
# each_async
# ==========

@Command(upper_)
async def paced_generator_cmd(loops:int, _delay:float=0.1):
    ''' Yields with a real await between items so the parent can observe them arriving separately.
    _delay is hidden so it can only be passed programmatically, not bound from the command line.
    '''
    for i in range(loops):
        await asyncio.sleep(_delay)
        yield {'value':['zero','one','two'][i]}


@Command()
def big_result_cmd(size:int):
    ''' One result far larger than a pipe buffer, so its frame spans many reads '''
    return 'x' * size


@pytest.mark.asyncio
async def test_each_async_call():
    ''' wait() collects each_async() the same way __call__() collects each() '''
    assert(await async_fn.instance().bind('3').wait() == '3')
    assert(await implicit_generator_cmd.instance().bind('0','upper').wait() == Command.no_return)
    assert(await implicit_generator_cmd.instance().bind('1','upper').wait() == 'ZERO')
    assert(await implicit_generator_cmd.instance().bind('2','upper').wait() == ('ZERO','ONE'))


@pytest.mark.asyncio
async def test_each_async_agrees_with_each():
    ''' The async path yields the same values in the same order as the sync path '''
    cmd = lambda: implicit_generator_async_cmd.instance().bind('3','upper')
    assert([x async for x in cmd().each_async()] == list(cmd().each()))


@pytest.mark.asyncio
async def test_each_async_arrives_incrementally():
    ''' The point of each_async(): values arrive as produced, not batched at child exit.
    This is what fails if the child's output pipe is left buffered without a flush.
    '''
    import time
    delay, arrivals = 0.1, []
    async for x in paced_generator_cmd.instance().bind('3','upper').each_async(_delay=delay):
        arrivals.append(time.monotonic())
    assert(len(arrivals) == 3)
    assert(arrivals[-1] - arrivals[0] > delay) # Batched delivery would make this ~0


@pytest.mark.asyncio
async def test_each_async_big_frame():
    ''' A record larger than the pipe buffer is reassembled from many reads '''
    size = 1024*1024
    assert(await big_result_cmd.instance().bind(str(size)).wait() == 'x'*size)


@pytest.mark.asyncio
async def test_each_async_mid_break():
    ''' Break in the middle of iteration.  The abandoned generator must not leak its child. '''
    agen = paced_generator_cmd.instance().bind('3','upper').each_async(_delay=0)
    async for x in agen:
        break
    assert(x == 'ZERO')
    await agen.aclose()


def _open_fd_count():
    ''' How many file descriptors does this process have open right now? '''
    import os
    return len(os.listdir('/dev/fd' if os.path.isdir('/dev/fd') else '/proc/self/fd'))


def test_each_no_fd_leak():
    ''' each() must close its own ends of the pipes it hands to the child '''
    cmd = lambda: implicit_generator_cmd.instance().bind('1','upper')()
    cmd() # Warm up, so one-time allocations aren't counted as a leak
    before = _open_fd_count()
    for _ in range(3): cmd()
    assert(_open_fd_count() == before)


@pytest.mark.asyncio
async def test_each_async_no_fd_leak():
    ''' each_async() must close its own ends of the pipes it hands to the child '''
    cmd = lambda: paced_generator_cmd.instance().bind('1','upper').wait(_delay=0)
    await cmd() # Warm up, so one-time allocations aren't counted as a leak
    before = _open_fd_count()
    for _ in range(3): await cmd()
    assert(_open_fd_count() == before)


@pytest.mark.asyncio
async def test_each_async_raise():
    ''' A generator can raise an exception '''
    with pytest.raises(IndexError) as e:
        async for x in implicit_generator_async_cmd.instance().bind('4','upper').each_async():
            pass
    assert(hasattr(e.value, 'traceback_text'))


@Command()
def pass_kw_to_pos_or_kw(pos_or_kw):
    return pos_or_kw

def test_pass_kw_to_pos_or_kw():
    ''' kwargs passed to args_kwargs() can set positional-or-keyword parameters
    '''
    result = pass_kw_to_pos_or_kw.instance()(pos_or_kw=9)
    assert(result == 9)


@pytest.mark.skip('implement')
def test_exceptions_deep():
    ''' execptions from deep children should be propigated to the top
    '''

@pytest.mark.skip('implement')
def test_exceptions_outside_try():
    ''' What happen to exceptions that are thrown in entry_point outside of the try section?
    '''
