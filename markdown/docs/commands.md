<a id="page-commands"></a>

# Commands

> * [Basic Example](#basic-example)
> * [Positional vs. Keyword](#positional-vs-keyword)
>   * [Positional](#positional)
>   * [Keyword](#keyword)
> * [Types](#types)
>   * [Bool](#bool)
>   * [Numbers](#numbers)
>   * [Lists](#lists)
>   * [Tuple](#tuple)
> * [Sub-Commands](#sub-commands)
>   * [Explicit Sub-command Control](#explicit-sub-command-control)
>   * [Implicit Sub-command Control](#implicit-sub-command-control)
>   * [Generators](#generators)
> * [Variable Args](#variable-args)
>   * [\*args](#args)
>   * [\*\*kwargs](#kwargs)
> * [Edge Cases / Quirks](#edge-cases-quirks)
>   * [Backslash Escape](#backslash-escape)
>   * [Hidden Parameters](#hidden-parameters)
>   * [Trailing Underscore](#trailing-underscore)
>   * [Skip Argument](#skip-argument)
> * [Class Documentation](#class-documentation)

The command line interface follows this generic pattern:

> [command <positional_argument>\* <keyword_argument>\*]+

A command is defined by a Python function decorated with [`@CLI`](#libclipy.core.command.dfn.CLI).
The function’s parameters and the associated docstring fully define the command’s interface and documentation.

## Basic Example

```python
@CLI
def hello(say, *, times__t=1):
    ''' Say something multiple times

    Parameters:
        <message>, --say <message>
            What you want to say
        --times <int>, -t <int>
            How many times you want to say it.
    '''
    return ' '.join([say] * times__t)
```

```console
$ ./cli.py hello -h
<hello.__doc__>
```

Using `-h` or `--help` will show the docstring documentation.

```console
$ ./cli.py hello -t 3 --say Ho
Ho Ho Ho
```

If the value returned from a command is not `None`, then it is pretty-printed.
You may use a single dash for single character names, otherwise use double-dashes.
Names defined with double underscores separate the aliases that can be used on the command line (`--times` or `-t`).

The `say` parameter has no type information so it will be a string.
The `times__t` parameter’s default value is an int, so you can only pass integers.  `-t hi` will fail with an error.

```console
$ ./cli.py "Hello World" -t=2
Hello World Hello World
```

Since the parameter `say` is defined as a keyword *or* positional, you can pass it positionally, as well.
But `times__t` is keyword only so it cannot be given positionally.

## Positional vs. Keyword

Positional parameters always precede keyword arguments (with the exception of `*args` as described later).

First, command line arguments are taken one by one until a dash argument (that might be a keyword) is encountered which indicates the start of keyword arguments.  Note that negative numbers don’t look like a keyword, so they are accepted as-is.

Next, keyword arguments are taken until a non-keyword (indicating the start of the next command), or `--` is encountered.

### Positional

```python
@CLI
def foo(a=3, /, banana__b='hi', *, carrot__c:int=None):
    ''' Foo

    Parameters:
        <int>
            Positional only
        <str>, --banana <str>, -b <str>
            Positional or keyword
        --carrot <int>, -c <int>
            Keyword only
    '''
    print(f"a={a}  banana={banana__b}  carrot={carrot__c}")
```

```console
$ ./cli.py foo 4 bye --carrot 42
a=4  banana='bye'  carrot=42

$ ./cli.py foo 4 -c 42 -b bye
a=4  banana='bye'  carrot=42
```

The distinction between positional-only, positional or keyword and keyword-only parameters is important.
Parameters before the `/` cannot be specified by name.  Parameters after the `*` *must* be given by name.
Other parameters may be given either way.

Notice how the docstring indicates which parameters may be given positionally.

### Keyword

Keyword parameters are given with the name (`-x`, `--bob`, `--etc`) followed by the value.
The value may follow the name after a space (`-x 3`), or be joined with an equals (`-x=3`).

Multi-letter names must use two dashes, and underscores are turned into dashes, so `a_long_name` becomes `--a-long-name`.
Single-letter names may use a single dash.

Double underscores separate name aliases, which is mostly used to give a short single-letter name along with the long name, `name__n`.
However, multiple aliases may be given. `super_long__medium__s__z`  would allow `--super-long`, `--medium`, `-s` and `-z`.

## Types

All parameters have a type which is determined by its annotation or default value.
If unknown, `str` is assumed.

<a id="bool-type"></a>

### Bool

```python
@CLI
def foo(*, verbose__v=False, times__t:int=None):
    print(f"v={verbose__v}  t={times__t}")
```

```console
$ ./cli.py foo -vt 100
v=True  t=100

$ ./cli.py foo -vvv
v=3  t=None
```

Flags are parameters of type `bool`.

Flags may be specified multiple times in which case the value won’t be `True`, but an integer specifying how many times it was given.
Since `int(True) == 1` you can use `int(verbose__v)` to get the number of times it was specified.

Flags may be joined with other single-letter names in the usual way. `-vvt x` is equivalent to `-v -v -t x`.
The last letter of the group may be a non-flag type, but the others *must* be `bool` typed.

Without a value, `True` is assumed, but you can specify the value in common (case-insensitive) ways:  `true/false`, `t/f`, `yes/no`, `y/n`, `on/off`, `1/0`.

### Numbers

`int` and `float`

Integers can be specified in various bases.

* base 2:  `0b1101`
* base 8:  `0755`
* base 10: `-53`
* base 16: `0xff`

Note that negative numbers can be used normally.  They won’t be treated as keyword names.

<a id="list-type"></a>

### Lists

```python
@CLI
def foo(a:int, b:list[float]=None, c=[]):
    print(f"a={a}  b={b}  c={c}")
```

Since the element type of the third list is unspecified, `str` is assumed.

Arguments are taken and added to the list until a keyword argument is encountered, or a single `-`.
For keyword parameters you can optionally repeat the name `-c 66 -c apples`.

```console
$ ./cli.py foo 3 1.1 -.1 1e3 - 66 apples
a=3  b=[1.1, -0.1, 1000.0]  c=['66', 'apples']

$ ./cli.py foo -c 66 -c apples -b 1.1 -0.1 1e3 - -a 3
a=3  b=[1.1, -0.1, 1000.0]  c=['66', 'apples']

$ ./cli.py foo 3 1.1 - -c 66 apples - -b -0.1 1e3
a=3  b=[1.1, -0.1, 1000.0]  c=['66', 'apples']
```

### Tuple

```python
@CLI
def foo(a:tuple[int,str], b=tuple[str], c=(1,2,3)):
    print(f"a={a}  b={b}  c={c}")
```

```console
$ ./cli.py foo 1,hi a,b,c 4,5,6
a=(1, 'hi')  b=('a', 'b', 'c')  c=(4, 5, 6)

$ ./cli.py foo -b x -a="1, space"
a=(1, ' space')  b=('x', )  c=(1, 2, 3)
```

Tuples are given as a comma-separated set of values.
The number of values is determined by the type.
If the tuple type specifies a single element type (e.g., `tuple[bool]`), then any number of values of that type may be given.

## Sub-Commands

A command may have sub-commands.
Sub-commands must be discoverable before execution starts, so they are given to the [`@CLI`](#libclipy.core.command.dfn.CLI) decorator.

The complete chain of commands is fully parsed before any commands are actually executed.
By making the sub-command lookup deterministic we can provide better help and documentation support.
Also, any command-line syntax errors in sub-commands are caught before anything is executed.

You can pass an entire module, or a string module path, or even individual commands ([`CommandDfn`](#libclipy.core.command.dfn.CommandDfn) objects).

By passing the module containing your commands as a string, it will be loaded only if a sub-command is actually called, which is generally preferred for efficiency.

Finally, you can also pass a callable.
Using a callable allows you to take more control over the loading of sub-commands.
You might, for example, want to ensure that necessary packages are installed lazily.

The callable will be given a string prefix (possibly empty) of a sub-command.
The callable must return one of the following:

- A list of zero or more matching [`CommandDfn`](#libclipy.core.command.dfn.CommandDfn) commands.  If the prefix is empty, all commands should be returned.
- A module (or string path) containing commands

If a command takes an initial positional-only parameter whose name starts with an underscore, then the sub-command [`Command`](#libclipy.core.command.command.Command) object will be passed to it.
Otherwise, the command’s return value is used to determine the default argument values passed to the sub-command.

<a id="explicit-control"></a>

### Explicit Sub-command Control

By explicitly receiving the sub-command [`Command`](#libclipy.core.command.command.Command) object, you are responsible for calling it however you want.

```python
import sub_module

@CLI
def sub_marine(_sub, /,  a, b):
    print(f"got: {_sub} {a} {b}")
    return a+b

@CLI('.lazy_loaded_module', sub_module, sub_marine)
def foo(_sub, /):
    print(f"result: {_sub(3, b=4)}")
```

The arguments passed when calling `_sub(3, b=4)` act as default values and may be overridden by arguments given from the command line.

```console
$ foo sub-marine 6
got: None 6 4
result: 10
```

<a id="implicit-control"></a>

### Implicit Sub-command Control

If the command does not take an initial, [hidden](#hidden-params), positional-only parameter, then the command’s return value is used to determine the default argument values passed to the sub-command.

In that case, the command is expected to return one of `None`, `*args`, `**kwargs`, or `*args, **kwargs`, to be given to the sub-command as default values.

```python
@CLI
def sub_sandwich(*args, **kwargs):
    print(f"args:{args} kwargs:{kwargs}")

@CLI(sub_sandwich)
def foo():
    return (3,4), dict(x=3)
```

```console
$ foo sub-sandwich
args:(3,4) kwargs:{'x':3}

$ foo sub-sandwich -x 9
args:(3,4) kwargs:{'x':9}

$ foo sub-sandwich -y hello bar
args:('bar',) kwargs:{'x':3, 'y':'hello'}
```

### Generators

Commands may be defined as generator functions (normal or async).

```python
@CLI
def ls(path):
    yield from os.listdir(path)

@CLI(ls)
def foo(_sub, /):
    print([f.upper() for f in _sub()])

@CLI(ls)
def bar():
    return '.'
```

If [implicit sub-command control](#implicit-control) is used, then the sub-command can be iterated over in the usual way.

```console
$ ./cli.py foo ls .
['CLI.PY', 'README.RST', ...]
```

If [explicit sub-command control](#explicit-control) is used, then the command’s results are collected into a list.

```console
$ ./cli.py bar ls
['cli.py', 'README.rst', ...]
```

## Variable Args

Both `*args` and `**kwargs` are usable features in commands.

<a id="var-args"></a>

### \*args

The [lists](#list-type) section above discussed how to get lists of values.
But that way has one unnatural limitation.
Keyword arguments must follow the positional arguments which is not nice when dealing with file globs.

By specifying `*args`, all unprocessed trailing arguments (after keyword arguments have been processed) are captured verbatim into `args`
Since the trailing arguments are all captured, a command with `*args` cannot have sub-commands.

```python
@CLI
def foo(first=None, *files, verbose__v=False):
    print(f"first={first!r}  verbose={verbose__v}  files={files}")
```

```console
$ ./cli.py foo *
first='cli.py'  verbose=False  files=('README.rst', ...)

$ ./cli.py foo - *
first=None  verbose=False  files=('cli.py', 'README.rst', ...)
```

In the first example, the first file name is captured by `first` and the remaining files would go to `files`.
In the second example, `first` is skipped so all files go to `files`.

Both the first and second examples have a tricky corner-case.
If you have a file that starts with a dash  *(why!?)*, then it might be treated as a keyword name and accidentally set the `verbose` flag, for example.
By explicitly ending the keyword section with `--` you can safely capture any weirdly-named files.

```console
$ ./cli.py foo hello -vv -- *
first='hello'  verbose=2  files=('cli.py', '--verbose', ...)
```

If your command does not take any keyword parameters (or `**kwargs`) then this is not an issue.

If your var-args parameter name starts with an underscore (e.g., `*_args`), then it is considered [hidden](#hidden-params) and will not capture additional command-line arguments.
However, extra positional arguments may still be passed programmatically when calling the sub-command (e.g., `_sub(1,2,3)`).

### \*\*kwargs

Arbitrary keyword arguments may be collected.
Values are typed as `str` by default, unless they appear in a [:ref:flag group](#bool-type), in which case they are typed as `bool`.

A double dash `--` can be used to force the end of the current command’s argument parsing.

```python
@CLI
def foo(a=False, **kwargs):
    print(f"a={a}  kwargs={kwargs}")
```

```console
$ ./cli.py foo -axd 33 --long-name hi,bye
a=True  kwargs={'x':True, 'd':'33', 'long_name':'hi,bye'}
```

## Edge Cases / Quirks

This section highlights some of the rarely encountered edge cases and quirks.

<a id="backslash"></a>

### Backslash Escape

In order to pass an argument value that starts with a dash (e.g., `-not-a-keyword`) you must escape the initial dash with a backslash.

**Note**: Values that do not look like keywords (e.g., negative numbers) do not need to be escaped.

```python
@CLI
def foo(x:list, y:int):
    print(f"x={x}  y={y}")
```

**Note**: The shell eats one backslash if you don’t surround the argument in quotes.

```console
$ ./cli.py foo \\-y -9 \\- -y -3
x=['-y', '-9', '-']  y=-3
```

For consistency, a single leading backslash is removed from any value during parsing.
The exception is arguments captured as [\*args](#var-args) are kept as-is without leading backslashes getting removed.

```console
$ ./cli.py foo \\\\hi \\ -y \\33
x=['\\hi', '']  y=33
```

Notice the argument with a single backslash `\\` becomes an empty string after the leading backslash is removed.

<a id="hidden-params"></a>

### Hidden Parameters

A single, leading underscore on a parameter marks it as ‘hidden’.
This means it will not be settable with command-line arguments, and it is not visible in generated documentation.
Such parameters are only usable programmatically.
This also applies to [\*args and \*\*kwargs](#var-args) parameters.

```python
@CLI
def bar(_sub, /, q, **_kwargs):
    print(f"bar: sub={_sub}  q={q}  kwargs={_kwargs}")

@CLI(bar)
def foo(_sub, /, _x=1, y=2, _z=3, t=4):
    print(f"foo: x={_x}  y={y}  z={_z}  t={t}")
    _sub(10, r=11)
```

```console
$ ./cli.py foo 6 7 bar
foo: x=1  y=6  z=3  t=7
bar: sub=None  q=10  kwargs={'r':11}

$ ./cli.py foo bar -r 11
Unknown keyword argument 'r'
```

### Trailing Underscore

By adding a single trailing underscore to your command name or parameter name, you can alias Python keywords.

```python
@CLI
def break_(if_, else_):
    print(f"if={if_}  else={else_}")
```

```console
$ ./cli.py break if=cookie else fix
if='cookie'  else='fix'
```

### Skip Argument

As stated in the section on [lists](#list-type), a single dash `-` ends the processing of that list and moves to the next parameter.

More generally, a single dash skips that parameter, even if it is not a `list`

```python
@CLI
def foo(x=1, y=[2,3]):
    print(f"x={x}  y={y}")
```

```console
$ ./cli.py foo - 4 5 6
x=1  y=[4, 5, 6]
```

In the same way that a single dash ends the current parameter, a double dash `--` ends the current command and starts parsing the next sub-command.

Note that since a single dash skips the current parameter, it is not possible to set an empty list to override the default.
There is no syntax for explicitly setting a list parameter to an empty list from the command-line.

```console
$ ./cli.py - -
x=1  y=[2,3]

$ ./cli.py -y -
x=1  y=[2,3]
```

## Class Documentation

### *class* libclipy.core.command.dfn.CommandDfn(\*\_)

This is a Python type that defines a command.

It holds information about the command such as, its name, parameters (`inspect.signature`)

Don’t create CommandDfn types directly.  Instead use the [`@CLI`](#libclipy.core.command.dfn.CLI) decorator.

### *class* libclipy.core.command.command.Command

A Command is an object of type [`CommandDfn`](#libclipy.core.command.dfn.CommandDfn).

You can bind arguments to it and then run it.

### *class* libclipy.core.command.dfn.CLI(\*args, need=None, sub_required=None)

This is a decorator used on functions to turn them into [`CommandDfn`](#libclipy.core.command.dfn.CommandDfn).
