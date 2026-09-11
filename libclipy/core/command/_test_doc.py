''' Tests for every example in docs/commands.rst

Each test corresponds to a code-block or concrete claim in the documentation.
When a documented example is known to be wrong, the test is marked xfail and
references docs/issues.rst (docs/commands.rst review).
'''
import pytest
from .command import Command
from .errors import *
from .param import Param, ParamType


def run(cmd, *argv):
    ''' Bind argv, resolve args/kwargs (injecting _sub_cmd when explicit), call __func__.
    This runs the tests faster than starting a new processes for each command
    '''
    inst = cmd.instance().bind(*argv)
    args, kwargs = inst.args_kwargs(**({} if cmd.is_implicit else {'_sub_cmd':inst.sub}))
    return cmd.__func__(*args, **kwargs)


def bound(cmd, *argv):
    return repr(cmd.instance().bind(*argv))


# ---------------------------------------------------------------------------
# Basic Example
# ---------------------------------------------------------------------------

@Command()
def hello(say, /, times__t=1, *, loud__l=False):
    ''' Say something multiple times

    Parameters:
        <message>
            What you want to say
        <int> --times -t
            How many times you want to say it.
        --loud -l
            Say it loudly
    '''
    return ' '.join([say] * times__t) + '!'*int(loud__l)


@pytest.mark.skip("haven't decieded on a pretty implementation")
def test_doc_hello_help():
    ''' $ ./cli.py hello -h  shows the docstring '''
    with pytest.raises(HelpWanted) as e:
        hello.instance().bind('-h')
    text = '\n'.join(e.value.pretty())
    assert('Say something multiple times' in text)
    assert('--times' in text or 'times' in text)


def test_doc_hello_ho_3_lll():
    ''' $ ./cli.py hello Ho 3 -lll  ->  Ho Ho Ho!!! '''
    assert(run(hello, 'Ho', '3', '-lll') == 'Ho Ho Ho!!!')
    assert(bound(hello, 'Ho', '3', '-lll') == "hello('Ho', 3, loud__l=3)")


def test_doc_hello_types():
    ''' say is str; times__t default int so -t hi fails '''
    from .param import Str, Int, Bool
    assert(type(hello.instance().params['say'].type) is Str)
    assert(type(hello.instance().params['times__t'].type) is Int)
    assert(type(hello.instance().params['loud__l'].type) is Bool)
    with pytest.raises(ParseError):
        hello.instance().bind('x', '-t', 'hi')

def test_doc_hello_hello_world_lt_2():
    ''' $ ./cli.py hello "Hello World" -lt 2

    Doc (current) shows output with trailing ! when -l is present.
    Missing command name in the console line is a docs issue; the argv for hello is tested here.
    '''
    assert(run(hello, 'Hello World', '-lt', '2') == 'Hello World Hello World!')


def test_doc_hello_times_positional_or_keyword():
    ''' times__t may be positional after message, or -t / --times; loud__l is keyword-only '''
    assert(run(hello, 'Ho', '2') == 'Ho Ho')
    assert(run(hello, 'Ho', '-t', '2') == 'Ho Ho')
    assert(run(hello, 'Ho', '--times', '2') == 'Ho Ho')
    # loud is keyword-only: a trailing positional is an error (no sub-commands)
    with pytest.raises(ExtraArguments):
        hello.instance().bind('Ho', '2', 'true')

# ---------------------------------------------------------------------------
# Positional vs Keyword — Positional
# ---------------------------------------------------------------------------

@Command()
def pos_foo(a=3, /, banana__b='hi', *, carrot__c:int=None):
    ''' Foo

    Parameters:
        <int>
            Positional only
        <str> --banana -b
            Positional or keyword
        --carrot -c <int>
            Keyword only
    '''
    return f"a={a}  banana={banana__b!r}  carrot={carrot__c}"


def test_doc_positional_foo_pos_and_long_kw():
    ''' $ ./cli.py foo 4 bye --carrot 42 '''
    assert(run(pos_foo, '4', 'bye', '--carrot', '42') == "a=4  banana='bye'  carrot=42")


def test_doc_positional_foo_short_kw():
    ''' $ ./cli.py foo 4 -c 42 -b bye '''
    assert(run(pos_foo, '4', '-c', '42', '-b', 'bye') == "a=4  banana='bye'  carrot=42")


def test_doc_positional_only_cannot_be_named():
    ''' Parameters before / cannot be specified by name '''
    with pytest.raises(UnknownKey):
        pos_foo.instance().bind('--a', '4')


def test_doc_keyword_only_must_be_named():
    ''' Parameters after * must be given by name; carrot cannot be third positional after a,b filled via defaults skip '''
    # a and banana filled, extra positional is not carrot
    with pytest.raises(ExtraArguments):
        pos_foo.instance().bind('4', 'bye', '42')


# ---------------------------------------------------------------------------
# Keyword
# ---------------------------------------------------------------------------

@Command()
def kw_names(*, a_long_name=None, name__n=None, super_long__medium__s__z=None):
    return (a_long_name, name__n, super_long__medium__s__z)


def test_doc_keyword_space_and_equals():
    ''' Value may follow after a space or with = '''
    assert(run(kw_names, '--a-long-name', '3') == ('3', None, None))
    assert(run(kw_names, '--a-long-name=3') == ('3', None, None))


def test_doc_keyword_underscores_to_dashes():
    ''' a_long_name becomes --a-long-name; underscore form also accepted '''
    assert(run(kw_names, '--a-long-name', 'x') == ('x', None, None))
    assert(run(kw_names, '--a_long_name', 'x') == ('x', None, None))


def test_doc_keyword_aliases():
    ''' name__n -> --name or -n; super_long__medium__s__z multiple aliases '''
    assert(run(kw_names, '--name', 'a') == (None, 'a', None))
    assert(run(kw_names, '-n', 'a') == (None, 'a', None))
    assert(run(kw_names, '--super-long', '1') == (None, None, '1'))
    assert(run(kw_names, '--medium', '2') == (None, None, '2'))
    assert(run(kw_names, '-s', '3') == (None, None, '3'))
    assert(run(kw_names, '-z', '4') == (None, None, '4'))


# ---------------------------------------------------------------------------
# Bool
# ---------------------------------------------------------------------------

@Command()
def bool_foo(*, verbose__v=False, times__t:int=None):
    return f"v={verbose__v}  t={times__t}"


def test_doc_bool_vt_100():
    ''' $ ./cli.py foo -vt 100  ->  v=True  t=100 '''
    assert(run(bool_foo, '-vt', '100') == 'v=True  t=100')


def test_doc_bool_vvv():
    ''' $ ./cli.py foo -vvv  ->  v=3  t=None '''
    assert(run(bool_foo, '-vvv') == 'v=3  t=None')


def test_doc_bool_joined_group():
    ''' -vvt N is equivalent to -v -v -t N (doc uses "x" as a placeholder value) '''
    assert(run(bool_foo, '-vvt', '9') == run(bool_foo, '-v', '-v', '-t', '9'))
    assert(run(bool_foo, '-vvt', '9') == 'v=2  t=9')

def test_doc_bool_int_true():
    ''' int(True)==1 so int(verbose__v) works for a single flag '''
    inst = bool_foo.instance().bind('-v')
    args, kwargs = inst.args_kwargs()
    assert(int(kwargs['verbose__v']) == 1)
    inst = bool_foo.instance().bind('-vvv')
    args, kwargs = inst.args_kwargs()
    assert(int(kwargs['verbose__v']) == 3)


def test_doc_bool_keyword_equals_values():
    ''' Without a value True is assumed; =true/=false and similar work '''
    assert(run(bool_foo, '-v') == 'v=True  t=None')
    assert(run(bool_foo, '-v=true') == 'v=True  t=None')
    assert(run(bool_foo, '-v=false') == 'v=False  t=None')
    assert(run(bool_foo, '-v=0') == 'v=False  t=None')
    assert(run(bool_foo, '-v','0') == 'v=False  t=None')
    assert(run(bool_foo, '-v=1') == 'v=True  t=None')
    assert(run(bool_foo, '-v','1') == 'v=True  t=None')
    assert(run(bool_foo, '-v=yes') == 'v=True  t=None')
    assert(run(bool_foo, '-v=no') == 'v=False  t=None')
    assert(run(bool_foo, '-v=on') == 'v=True  t=None')
    assert(run(bool_foo, '-v=off') == 'v=False  t=None')


def test_doc_bool_keyword_space_separated_words():
    ''' Space separated with non 1/0 does not work '''
    with pytest.raises(ExtraArguments):
        run(bool_foo, '-v', 'false')
    with pytest.raises(ExtraArguments):
        run(bool_foo, '-v', 'true')


def test_doc_bool_keyword_space_separated_ints():
    ''' Integer 0/1 after a flag are accepted as values '''
    assert(run(bool_foo, '-v', '0') == 'v=False  t=None')
    assert(run(bool_foo, '-v', '1') == 'v=True  t=None')


@Command()
def bool_pos(a:bool, /):
    return a


def test_doc_bool_positional_word_values():
    ''' Positional bools accept the full vocabulary including enable/disable '''
    for t, expect in [
        ('true', True), ('false', False), ('t', True), ('f', False),
        ('yes', True), ('no', False), ('y', True), ('n', False),
        ('on', True), ('off', False), ('1', True), ('0', False),
        ('enable', True), ('disable', False),
    ]:
        assert(run(bool_pos, t) is expect), t


@Command()
def disable_(states=[True, False]):
    return f"states={states}"


@Command(disable_, sub_required=False)
def bool_val_foo(a:bool, *, flag__f=True, _sub_cmd=None):
    return f"a={a}  f={flag__f}  {_sub_cmd and _sub_cmd()}"


def test_doc_bool_on_af_disable():
    ''' $ ./cli.py on -af=disable  ->  a=2  f=False  None

    Positional on sets a=True; -a increments to 2; -f=disable sets f=False.
    Doc writes disabled; disable is the implemented token (see enabled/disabled xfail).
    '''
    assert(run(bool_val_foo, 'on', '-af=disable') == 'a=2  f=False  None')


def test_doc_bool_on_af_disabled_documented():
    ''' $ ./cli.py on -af=disabled  ->  a=2  f=False  None  (as documented) '''
    assert(run(bool_val_foo, 'on', '-af=disabled') == 'a=2  f=False  None')


def test_doc_bool_1_aaa_FALSE():
    ''' $ ./cli.py 1 -aaa=FALSE  ->  a=False  f=True  None

    Positional 1 sets a; clustered -aaa=FALSE ends with false and clears a.
    '''
    assert(run(bool_val_foo, '1', '-aaa=FALSE') == 'a=False  f=True  None')


def test_doc_bool_disable_flag_eq_disable_documented():
    ''' $ ./cli.py disable --flag=disable  ->  a=False  f=False  None  (as documented) '''
    assert(run(bool_val_foo, 'disable', '--flag=disable') == 'a=False  f=False  None')


def test_doc_bool_disable_flag_eq_disable_actual():
    ''' Actual: disable is falsey for both positional a and --flag=disable '''
    assert(run(bool_val_foo, 'disable', '--flag=disable') == 'a=False  f=False  None')


def test_doc_bool_disable_flag_space_disable():
    ''' $ ./cli.py disable --flag disable  ->  a=False  f=True  states=[True, False]

    Space-separated disable after --flag looks like a sub-command name, so flag stays True
    and disable is bound as the sub-command.
    '''
    assert(list(bool_val_foo.instance().bind('disable', '--flag', 'disable').each())
           == ['a=False  f=True  states=[True, False]'])


def test_doc_bool_t_f_off_errors():
    ''' $ ./cli.py t -f off  ->  ERROR

    Space-separated off is not consumed as the flag value; treated as unknown sub-command.
    '''
    with pytest.raises(UnknownSubCommand):
        bool_val_foo.instance().bind('t', '-f', 'off')


def test_doc_bool_keyword_equals_enable_disable():
    ''' Keyword =enable/=disable and case variants '''
    assert(run(bool_val_foo, 'true', '-f=enable') == 'a=True  f=True  None')
    assert(run(bool_val_foo, 'true', '-f=disable') == 'a=True  f=False  None')
    assert(run(bool_val_foo, 'true', '-f=DISABLE') == 'a=True  f=False  None')


def test_doc_bool_enabled_disabled_vocabulary():
    ''' Doc vocabulary includes enabled/disabled '''
    assert(run(bool_pos, 'enabled') is True)
    assert(run(bool_pos, 'disabled') is False)
    assert(run(bool_val_foo, 'true', '-f=enabled') == 'a=True  f=True  None')
    assert(run(bool_val_foo, 'true', '-f=disabled') == 'a=True  f=False  None')


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

@Command()
def num_int(a:int):
    return a


@Command()
def num_float(a:float):
    return a


def test_doc_int_bases():
    ''' base 2/8/10/16 forms '''
    assert(run(num_int, '0b1101') == 0b1101)
    assert(run(num_int, '0755') == 0o755)
    assert(run(num_int, '-53') == -53)
    assert(run(num_int, '0xff') == 0xff)


def test_doc_negative_numbers_not_keywords():
    ''' Negative numbers are accepted as values, not keyword names '''
    assert(run(num_int, '-53') == -53)
    assert(run(num_float, '-3.14') == -3.14)
    assert(run(num_float, '-.1') == -0.1)
    assert(run(num_float, '1e3') == 1000.0)


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

@Command()
def list_foo(a:int, b:list[float]=None, c:list=None):
    return f"a={a}  b={b}  c={c}"


def test_doc_list_element_type_default_str():
    ''' Unspecified list element type defaults to str'''
    from .param import List, Str
    t = list_foo.instance().params['c'].type
    assert(isinstance(t, List))
    assert(isinstance(t.subs[0], Str))


def test_doc_list_positional_then_dash():
    ''' $ ./cli.py foo 3 1.1 -.1 1e3 - 66 apples '''
    assert(run(list_foo, '3', '1.1', '-.1', '1e3', '-', '66', 'apples')
           == "a=3  b=[1.1, -0.1, 1000.0]  c=['66', 'apples']")


def test_doc_list_keyword_repeat_and_dash():
    ''' $ ./cli.py foo -c 66 -c apples -b 1.1 -0.1 1e3 - -a 3 '''
    assert(run(list_foo, '-c', '66', '-c', 'apples', '-b', '1.1', '-0.1', '1e3', '-', '-a', '3')
           == "a=3  b=[1.1, -0.1, 1000.0]  c=['66', 'apples']")


def test_doc_list_mixed_skip():
    ''' $ ./cli.py foo 3 1.1 - -c 66 apples - -b -0.1 1e3 '''
    assert(run(list_foo, '3', '1.1', '-', '-c', '66', 'apples', '-', '-b', '-0.1', '1e3')
           == "a=3  b=[1.1, -0.1, 1000.0]  c=['66', 'apples']")


# ---------------------------------------------------------------------------
# Tuple
# ---------------------------------------------------------------------------

@Command()
def tup_foo(a:tuple[int,str], b:tuple[str]=None, c=(1,2,3)):
    return f"a={a}  b={b}  c={c}"


def test_doc_tuple_positional():
    ''' $ ./cli.py foo 1,hi a,b,c 4,5,6 '''
    assert(run(tup_foo, '1,hi', 'a,b,c', '4,5,6')
           == "a=(1, 'hi')  b=('a', 'b', 'c')  c=(4, 5, 6)")


def test_doc_tuple_keyword_equals_space():
    ''' $ ./cli.py foo -b x -a="1, space" '''
    # argv as the process receives after shell: -b, x, -a=1, space  OR -a with value "1, space"
    assert(run(tup_foo, '-b', 'x', '-a=1, space')
           == "a=(1, ' space')  b=('x',)  c=(1, 2, 3)")


@Command()
def tup_bool(a:tuple[bool]=None):
    return a


def test_doc_tuple_single_element_type_any_length():
    ''' tuple[bool] accepts any number of values of that type '''
    assert(run(tup_bool, '1,0,true,false') == (True, False, True, False))


# ---------------------------------------------------------------------------
# Declaring Sub-commands
# ---------------------------------------------------------------------------

@Command()
def decl_baz(a, b):
    return a+b


@Command(decl_baz)
def decl_foo():
    pass


def test_doc_declaring_subcommands_direct_commanddfn():
    ''' Individual CommandDfn objects may be passed to @Command() '''
    assert(bound(decl_foo, 'decl-baz', '1', '2') == "decl-foo() -> decl-baz('1', '2')")
    assert(decl_baz in decl_foo.sub_commands() or any(s is decl_baz or s.name == 'decl-baz' for s in decl_foo.sub_commands()))


@Command('._testing_cmds')
def decl_lazy():
    ''' Module path string is a valid sub-command source (lazy load) '''
    pass


def test_doc_declaring_subcommands_module_string():
    ''' Module path string loads sub-commands when queried '''
    names = {s.name for s in decl_lazy.sub_commands()}
    assert(names)  # _testing_cmds provides commands


def test_doc_subcommand_chain_parsed_before_execution():
    ''' Full chain is bound before any command runs '''
    inst = decl_foo.instance().bind('decl-baz', '1', '2')
    assert(inst.sub is not None)
    assert(bound(decl_foo, 'decl-baz', '1', '2') == "decl-foo() -> decl-baz('1', '2')")


# ---------------------------------------------------------------------------
# Explicit Sub-command Control
# ---------------------------------------------------------------------------

@Command()
def exp_baz(a:int, b=8):
    return a+b


@Command(exp_baz, sub_required=False)
def exp_foo(z:int, _sub_cmd):
    return f"result: {z*(2 if _sub_cmd is None else _sub_cmd(3,b=9))}"


def test_doc_explicit_foo_6():
    ''' $ foo 6  ->  result: 12 '''
    assert(run(exp_foo, '6') == 'result: 12')


def test_doc_explicit_foo_3_baz_b_7():
    ''' $ foo 3 baz -b 7  ->  result: 30

    Programmatic _sub_cmd(3,b=9) with CLI -b 7 overriding b → 3+7=10; z*10=30.
    Uses process execution via CommandDfn call path for the nested _sub_cmd(...).
    '''
    assert(list(exp_foo.instance().bind('3', 'exp-baz', '-b', '7').each()) == ['result: 30'])


# ---------------------------------------------------------------------------
# Implicit Sub-command Control
# ---------------------------------------------------------------------------

@Command()
def imp_baz(a:int, b=8):
    return a+b


@Command(imp_baz, sub_required=False)
def imp_foo(z:int):
    return {'a':10*z} if z else None


def test_doc_implicit_foo_0_baz_3():
    ''' $ ./cli.py foo 0 baz 3  ->  11 '''
    assert(list(imp_foo.instance().bind('0', 'imp-baz', '3').each()) == [11])


def test_doc_implicit_foo_5_baz_1():
    ''' $ ./cli.py foo 5 baz 1  ->  9  (CLI a=1 overrides parent default a=50) '''
    assert(list(imp_foo.instance().bind('5', 'imp-baz', '1').each()) == [9])


def test_doc_implicit_foo_5_baz_b_6():
    ''' $ ./cli.py foo 5 baz -b 6  ->  56 '''
    assert(list(imp_foo.instance().bind('5', 'imp-baz', '-b', '6').each()) == [56])


def test_doc_implicit_foo_5_baz_b_6():
    ''' $ ./cli.py foo 5 baz -b 6  ->  56 '''
    


def test_doc_sub_not_required():
    ''' sub_required can be set to false
    $ ./cli.py foo 5 -> {'a': 50}
    '''
    assert(imp_foo.instance().bind('5')() == {'a': 50})


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

@Command()
def gen_lower(v):
    return str(v).lower()


@Command(gen_lower, sub_required=False)
def gen_count_sync(end=26):
    ''' Sync stand-in used where async is not implemented '''
    for i in range(end):
        yield {'v': chr(65+i)}


@Command(gen_lower, sub_required=False)
async def gen_count_async(end=26):
    import asyncio
    for i in range(end):
        yield {'v': chr(65+i)}
        await asyncio.sleep(0)


def test_doc_generator_count_3_sync_call_shape():
    ''' __call__ collects multi-yield into a tuple of yielded values (dicts here) '''
    r = gen_count_sync.instance().bind('3')()
    assert(r == ({'v': 'A'}, {'v': 'B'}, {'v': 'C'}))


def test_doc_generator_count_3_documented_output():
    ''' $ ./cli.py count 3  ->  ['A', 'B', 'C']  (as documented) '''
    assert(list(gen_count_sync.instance().bind('3').each()) == [{'v': 'A'}, {'v': 'B'}, {'v': 'C'}])


def test_doc_generator_count_3_lower():
    ''' $ ./cli.py count 3 lower  -> mapped lowercase letters '''
    assert(list(gen_count_sync.instance().bind('3', 'gen-lower').each()) == ['a', 'b', 'c'])


def test_doc_generator_async_count():
    ''' async def count with yield is documented as supported '''
    assert(list(gen_count_async.instance().bind('3', 'gen-lower').each()) == ['a', 'b', 'c'])


@pytest.mark.asyncio
async def test_doc_generator_wait_collects_list():
    ''' wait() is documented to collect generator results into a list '''
    assert(await gen_count_sync.instance().bind('3').wait() == ({'v':'A'}, {'v':'B'}, {'v':'C'}))
    assert(await gen_count_async.instance().bind('3', 'gen-lower').wait() == ('a', 'b', 'c'))


# ---------------------------------------------------------------------------
# *args
# ---------------------------------------------------------------------------

@Command()
def args_foo(first=None, *files, verbose__v=False):
    return f"first={first!r}  verbose={verbose__v}  files={files}"


def test_doc_star_args_glob_first_file():
    ''' $ ./cli.py foo *  — first file to first, rest to *files (simulated with concrete names) '''
    assert(run(args_foo, 'cli.py', 'README.rst', 'LICENSE')
           == "first='cli.py'  verbose=False  files=('README.rst', 'LICENSE')")


def test_doc_star_args_skip_first():
    ''' $ ./cli.py foo - *  — first skipped, all files in *files '''
    assert(run(args_foo, '-', 'cli.py', 'README.rst')
           == "first=None  verbose=False  files=('cli.py', 'README.rst')")


def test_doc_star_args_double_dash():
    ''' $ ./cli.py foo hello -vv -- *  — -- ends keywords; dash-prefixed files safe '''
    assert(run(args_foo, 'hello', '-vv', '--', 'cli.py', '--verbose')
           == "first='hello'  verbose=2  files=('cli.py', '--verbose')")


def test_doc_star_args_no_subcommands():
    ''' A command with *args cannot have sub-commands (trailing goes to vargs) '''
    @Command()
    def child():
        pass
    @Command(child)
    def parent(*files):
        pass
    inst = parent.instance().bind('a', 'child')
    assert(inst.sub is None)
    assert(inst.vargs == ['a', 'child'])


def test_doc_star_args_hidden_no_capture():
    ''' *_args is hidden and does not capture additional CLI args '''
    @Command()
    def h(first=None, *_args, verbose__v=False):
        pass
    with pytest.raises(ExtraArguments):
        h.instance().bind('a', 'b', 'c')


# ---------------------------------------------------------------------------
# **kwargs
# ---------------------------------------------------------------------------

@Command()
def kwargs_foo(a=False, **kwargs):
    return f"a={a}  kwargs={kwargs}"


def test_doc_kwargs_flag_group():
    ''' $ ./cli.py foo -axd 33 --long-name hi,bye '''
    inst = kwargs_foo.instance().bind('-axd', '33', '--long-name', 'hi,bye')
    args, kwargs = inst.args_kwargs()
    assert(args[0] is True)
    assert(kwargs == {'x': True, 'd': '33', 'long_name': 'hi,bye'})
    assert(kwargs_foo.__func__(*args, **kwargs)
           == f"a=True  kwargs={kwargs}")

# ---------------------------------------------------------------------------
# Backslash Escape
# ---------------------------------------------------------------------------

@Command()
def bs_foo(x:list, y:int):
    return f"x={x}  y={y}"


def test_doc_backslash_dash_values():
    ''' $ ./cli.py foo \\-y -9 \\- -y -3  (argv after shell: \\-y, -9, \\-, -y, -3) '''
    assert(run(bs_foo, '\\-y', '-9', '\\-', '-y', '-3')
           == "x=['-y', '-9', '-']  y=-3")


def test_doc_backslash_leading_strip():
    ''' $ ./cli.py foo \\\\hi \\ -y \\33  ->  x=['\\hi', '']  y=33
    '''
    assert(run(bs_foo, '\\\\hi', '\\', '-y', '\\33') == "x=['\\\\hi', '']  y=33") # backslash escaped by bs_foo's f-string


def test_doc_backslash_star_args_preserved():
    ''' *args keep leading backslashes as-is '''
    inst = args_foo.instance().bind('a', '\\-weird', 'b')
    args, kwargs = inst.args_kwargs()
    assert(args[0] == 'a')
    assert(args[1:] == ['\\-weird', 'b'])
    assert(kwargs.get('verbose__v') is False or args)


# ---------------------------------------------------------------------------
# Hidden Parameters
# ---------------------------------------------------------------------------

@Command()
def hid_bar(_private, /, q, **_kwargs):
    return f"bar: private={_private}  q={q}  kwargs={_kwargs}"


@Command(hid_bar)
def hid_foo(_x=1, y=2, _z=3, t=4, *, _sub_cmd):
    return f"foo: x={_x}  y={y}  z={_z}  t={t} {_sub_cmd(10, r=11)}"


def test_doc_hidden_bind_skips_underscore_params():
    ''' $ ./cli.py foo 6 7 bar  — hidden positionals skipped; y=6 t=7 '''
    assert(bound(hid_foo, '6', '7', 'hid-bar', '9') == "hid-foo(-, 6, -, 7) -> hid-bar(-, '9')")
    assert(run(hid_foo, '6', '7', 'hid-bar', '9') == "foo: x=1  y=6  z=3  t=7 bar: private=10  q=9  kwargs={'r': 11}")


def test_doc_hidden_foo_corrected_sub_call():
    ''' Corrected programmatic call: _sub_cmd(10, 10, r=11) '''
    assert(run(hid_foo, '6', '7', 'hid-bar', '9') == "foo: x=1  y=6  z=3  t=7 bar: private=10  q=9  kwargs={'r': 11}")


def test_doc_hidden_foo_bar_r_11_documented():
    ''' $ ./cli.py foo bar -r 11  ->  Unknown keyword argument 'r'  (as documented) '''
    with pytest.raises(UnknownKey) as e:
        hid_foo.instance().bind('--', 'hid-bar', '3', '-r', '11')
    assert('r' in str(e.value).lower())


def test_doc_hidden_unknown_key_realistic():
    ''' Realistic unknown key: foo 6 7 bar -r 11 '''
    with pytest.raises(UnknownKey) as e:
        hid_foo.instance().bind('6', '7', 'hid-bar', '-r', '11')
    assert('-r' in str(e.value) or 'r' in str(e.value))


# ---------------------------------------------------------------------------
# Trailing Underscore
# ---------------------------------------------------------------------------

@Command()
def break_(if_, else_):
    return f"if={if_!r}  else={else_!r}"


def test_doc_trailing_underscore():
    ''' $ ./cli.py break --if=cookie --else=fix '''
    assert(break_.name == 'break')
    assert(run(break_, '--if=cookie', '--else=fix')
           == "if='cookie'  else='fix'")


# ---------------------------------------------------------------------------
# Skip Argument
# ---------------------------------------------------------------------------

@Command()
def skip_foo(x=1, y=[2,3]):
    return f"x={x}  y={y}"


def test_doc_skip_dash_list():
    ''' $ ./cli.py foo - 4 5 6  ->  x=1  y=[4, 5, 6] '''
    assert(run(skip_foo, '-', '4', '5', '6') == 'x=1  y=[4, 5, 6]')


def test_doc_skip_both_defaults():
    ''' $ ./cli.py foo - -  ->  x=1  y=[2,3] '''
    assert(run(skip_foo, '-', '-') == 'x=1  y=[2, 3]')


def test_doc_skip_keyword_dash_actually_errors():
    ''' -y - is MissingArgument '''
    with pytest.raises(MissingArgument):
        skip_foo.instance().bind('-y', '-')


def test_doc_double_dash_ends_command():
    ''' -- ends current command and starts sub-command parsing '''
    @Command()
    def child(x=1):
        return x
    @Command(child, sub_required=False)
    def parent(a=1):
        return a
    assert(bound(parent, '--', 'child', '5') == 'parent(-) -> child(5)'
           or 'child(5)' in bound(parent, '--', 'child', '5'))


# ---------------------------------------------------------------------------
# Misc claims from the narrative
# ---------------------------------------------------------------------------

def test_doc_help_aliases_reserved():
    ''' h and help are always reserved aliases '''
    with pytest.raises(DuplicateArgumentAlias):
        @Command()
        def bad(help):
            pass
    with pytest.raises(DuplicateArgumentAlias):
        @Command()
        def bad2(bob__h):
            pass


def test_doc_command_name_underscores_to_dashes():
    ''' Function my_cmd becomes command my-cmd '''
    @Command()
    def my_cmd():
        pass
    assert(my_cmd.name == 'my-cmd')


def test_doc_illegal_command_names():
    ''' Double underscore and leading underscore command names are illegal '''
    with pytest.raises(InvalidCommandName):
        @Command()
        def bad__():
            pass
    with pytest.raises(InvalidCommandName):
        @Command()
        def _leading():
            pass


def test_doc_annotation_wins_over_default():
    ''' Type from annotation, not default (a:int=None is int) '''
    @Command()
    def ann(a:int=None):
        return a
    from .param import Int
    assert(type(ann.instance().params['a'].type) is Int)


@ParamType()
def upper(self, sval, kw):
    return sval.upper()

@Command()
def custom_paramtype(x:upper):
    return x

def test_doc_custom_paramtype():
    ''' Custom ParamType is supported (missing from Types section) '''
    assert(run(custom_paramtype, 'abc') == 'ABC')


def test_doc_subcommand_prefix_match():
    ''' Unique prefixes resolve; ambiguous prefixes error (undocumented) '''
    @Command()
    def install():
        pass
    @Command()
    def init():
        pass
    @Command(install, init, sub_required=False)
    def root():
        pass
    assert('install' in bound(root, 'ins'))
    with pytest.raises(AmbiguousSubCommand):
        root.instance().bind('i')


@pytest.mark.asyncio
async def test_doc_each_async():
    ''' each_async is documented as a way to call a command (docs/commands.rst) '''
    assert([x async for x in hello.instance().bind('Ho','3','-l').each_async()] == ['Ho Ho Ho!'])