.. _page-commands:

=========
Commands
=========

.. contents::
    :local:

The command line interface follows this generic pattern:

    [command <positional_argument>* <keyword_argument>*]+

A command is defined by a Python function decorated with `@Command() <Command.__new__>`.
These are the various entrypoints to the project.
They execute in their own process and may have their own, unique, `virtual environment <Venv>`.
The function's parameters and the associated docstring fully define the command's interface and documentation.


Basic Example
==============

.. code-block:: python

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


.. code-block:: console

   $ ./cli.py hello -h
   <hello.__doc__>


Using ``-h`` or ``--help`` will show the docstring documentation.

.. code-block:: console

    $ ./cli.py hello Ho 3 -lll
    Ho Ho Ho!!!

If the value returned from a command is not ``None``, then it is pretty-printed (or json-printed).
You may use a single dash for single character names, otherwise use double-dashes.
Names defined with double underscores separate the aliases that can be used on the command line (``--times`` or ``-t``).

The ``say`` parameter has no type information so it will be a string.
The ``times__t`` parameter's default value is an int, so you can only pass integers.  ``-t hi`` will fail with an error.

.. code-block:: console

   $ ./cli.py "Hello World" -lt 2
   Hello World Hello World

Since the parameter ``times__t`` is defined as a keyword *or* positional, you can pass it positionally after the message, or explicitly with ``-t`` or ``--times``.
But ``loud__l`` is keyword-only so it cannot be given positionally.



Positional vs. Keyword
=======================

Positional parameters always precede keyword arguments, with the exception of ``*args`` as described later (`var-args <var-args>`).

First, command line arguments are taken one by one until a dash argument (that might be a keyword) is encountered which indicates the start of keyword arguments.  Note that negative numbers don't look like a keyword, so they are accepted as-is.

Next, keyword arguments are taken until a non-keyword (indicating the start of the next command), or ``--`` is encountered.


Positional
-----------


.. code-block:: python

    @Command()
    def foo(a=3, /, banana__b='hi', *, carrot__c:int=None):
        ''' Foo

        Parameters:
            <int>
                Positional only
            <str> --banana -b
                Positional or keyword
            --carrot -c <int>
                Keyword only
        '''
        print(f"a={a}  banana={banana__b}  carrot={carrot__c}")

.. code-block:: console

    $ ./cli.py foo 4 bye --carrot 42
    a=4  banana='bye'  carrot=42
    
    $ ./cli.py foo 4 -c 42 -b bye
    a=4  banana='bye'  carrot=42
    

The distinction between positional-only, positional or keyword and keyword-only parameters is important.
Parameters before the ``/`` cannot be specified by name.  Parameters after the ``*`` *must* be given by name.
Other parameters may be given either way.

Notice how the docstring indicates which parameters may be given positionally.


Keyword
--------

Keyword parameters are given with the name, ``-x``, ``--bob``, ``--etc``, followed by the value.
The value may follow the name after a space, ``-x 3``, or be joined with an equals, ``-x=3``.

Multi-letter names must use two dashes, and underscores are turned into dashes, so ``a_long_name`` becomes ``--a-long-name``.
Single-letter names may use a single dash.

Double underscores separate name aliases, which is mostly used to give a short single-letter name along with the long name, ``name__n``.
However, multiple aliases may be given. ``super_long__medium__s__z``  would allow ``--super-long``, ``--medium``, ``-s`` and ``-z``.



Types
======

All parameters have a type which is determined by its annotation or default value.
If unknown, ``str`` is assumed.


.. _bool-type:

Bool
-----

.. code-block:: python

    @Command()
    def foo(*, verbose__v=False, times__t:int=None):
        print(f"v={verbose__v}  t={times__t}")

.. code-block:: console

    $ ./cli.py foo -vt 100
    v=True  t=100
    
    $ ./cli.py foo -vvv
    v=3  t=None
    

Flags are parameters of type ``bool``.

Flags may be specified multiple times in which case the value won't be ``True``, but an integer specifying how many times it was given.
Since ``int(True) == 1`` you can use ``int(verbose__v)`` to get the number of times it was specified.

Flags may be joined with other single-letter names in the usual way. ``-vvt x`` is equivalent to ``-v -v -t x``.
The last letter of the group may be a non-flag type, but the others *must* be ``bool`` typed.

Without a value, ``True`` is assumed, but you can specify the value in common (case-insensitive) ways:  ``true/false``, ``t/f``, ``yes/no``, ``y/n``, ``on/off``, ``1/0``.


Numbers
---------

``int`` and ``float``

Integers can be specified in various bases.

* base 2:  ``0b1101``
* base 8:  ``0755``
* base 10: ``-53``
* base 16: ``0xff``

Note that negative numbers can be used normally.  They won't be treated as keyword names.

.. _list-type:

Lists
------

.. code-block:: python

    @Command()
    def foo(a:int, b:list[float]=None, c=[]):
        print(f"a={a}  b={b}  c={c}")

Since the element type of the third list is unspecified, ``str`` is assumed.

Arguments are taken and added to the list until a keyword argument is encountered, or a single ``-``.
For keyword parameters you can optionally repeat the name ``-c 66 -c apples``.


.. code-block:: console

    $ ./cli.py foo 3 1.1 -.1 1e3 - 66 apples
    a=3  b=[1.1, -0.1, 1000.0]  c=['66', 'apples']
    
    $ ./cli.py foo -c 66 -c apples -b 1.1 -0.1 1e3 - -a 3
    a=3  b=[1.1, -0.1, 1000.0]  c=['66', 'apples']

    $ ./cli.py foo 3 1.1 - -c 66 apples - -b -0.1 1e3
    a=3  b=[1.1, -0.1, 1000.0]  c=['66', 'apples']



Tuple
-------

.. code-block:: python

    @Command()
    def foo(a:tuple[int,str], b:tuple[str]=None, c=(1,2,3)):
        print(f"a={a}  b={b}  c={c}")

.. code-block:: console

    $ ./cli.py foo 1,hi a,b,c 4,5,6
    a=(1, 'hi')  b=('a', 'b', 'c')  c=(4, 5, 6)
    
    $ ./cli.py foo -b x -a="1, space"
    a=(1, ' space')  b=('x',)  c=(1, 2, 3)
    
Tuples are given as a comma-separated set of values.
The number of values is determined by the type.
If the tuple type specifies a single element type (e.g., ``tuple[bool]``), then any number of values of that type may be given.


.. _sub_commands:

Sub-commands
==============

A command may have sub-commands. 

Declaring Sub-commands
-------------------------

Sub-commands must be discoverable before execution of the first command starts, so they are given to the `@Command() <Command.__new__>` decorator.

The complete chain of commands is fully parsed before any commands are actually executed.
By making the sub-command lookup deterministic we can provide better help and documentation support.
Also, any command-line parse errors in sub-commands are caught before anything is executed.

You can pass an entire module, a module path string, or even individual commands (`CommandDfn` objects) to the `@Command() <Command.__new__>` decorator.

By passing the module containing your commands as a string, it will be loaded only if a sub-command is actually called, which is generally preferred for loading efficiency.

See the Command.__new__ documentation for more detail on the parameters to the decorator.

.. code-block:: python

    import sub_module

    @Command()
    def baz(a, b):
        return a+b

    @Command('..lazy.loaded', baz, sub_module)
    def foo():
        pass


Calling Sub-commands
---------------------

You can opt-in to receive the sub-command `Command` object so that you can call it explicitly however you want.
Or, you can let the sub-command get implicitly called after the command returns.

.. _explicit-control:

Explicit Sub-command Control
-----------------------------

In order to opt-in for explicit control you declare a keyword parameter named ``_sub_cmd`` (:ref:`hidden <hidden-params>`).
That parameter will receive the sub-command `Command` object, or ``None`` if this is the last command in the chain.

You are free to call the sub-command (`__call__()`, `each()`, `wait()`, `each_async()`) zero or any number of times.
The arguments you give to the sub-command will be used as defaults and may be overridden with arguments bound from the command-line.

.. code-block:: python

    @Command()
    def baz(a:int, b=8):
        return a+b

    @Command(baz)
    def foo(z:int, _sub_cmd):
        print(f"result: {z*(2 if _sub_cmd is None else _sub_cmd(3,b=9))}")

.. code-block:: console

    $ foo 6
    result: 12

    $ foo 3 baz -b 7
    result: 30


.. _implicit-control:

Implicit Sub-command Control
-----------------------------

If the command does not need explicit control of the sub-command then it does not define the ``_sub_cmd`` parameter and the sub-command will called implicitly after the command returns.
The return value of the command will be used as default keyword arguments to the sub-command, so it must return a dict, or ``None``.

Normally, in the implicit case, the return value of the sub-command will be passed up to the parent.
But, if the command does not have a sub-command then its return value (any value) will be returned to the parent.

There is a ``sub_required`` flag to the `@Command() <Command.__new__>` decorator that ensures (by default) that a sub command is given (if it has children).

.. code-block:: python

    @Command()
    def baz(a:int, b=8):
        return a+b

    @Command(baz, sub_required=True)
    def foo(z:int):
        return {'a':10*z} if z else None

.. code-block:: console

    $ ./cli.py foo 0 baz 3
    11

    $ ./cli.py foo 5 baz 1
    9

    $ ./cli.py foo 5 baz -b 6
    56



Generators
-----------

Commands may be defined as generator functions (normal or async).

.. code-block:: python

    @Command()
    def lower(v):
        return str(v).lower()

    @Command(lower, sub_required=False)
    async def count(end=26):
        for i in range(end):
            yield {'v':chr(65+i)}
            await asyncio.sleep(1)

When a generator is called using `__call__() <Command.__call__>` or `wait()` then its results are collected into a list and returned.

.. code-block:: console

    $ ./cli.py count 3

    ['A', 'B', 'C']

When a generator uses :ref:`implicit sub-command control <implicit-control>` then the sub-command is mapped over the generator's results.
The sub-command is called for each yielded parent value.

.. code-block:: console

    $ ./cli.py count 3 lower

    ['a', 'b', 'c']




Variable Args
==============

Both ``*args`` and ``**kwargs`` are usable features in commands.

.. _var-args:

\*args
-------

The :ref:`lists <list-type>` section above discussed how to get lists of values.
But that way has one unnatural limitation.
Keyword arguments must follow the positional arguments which is not nice when dealing with file globs.

By specifying ``*args``, all unprocessed trailing arguments (after keyword arguments have been processed) are captured verbatim into ``args``
Since the trailing arguments are all captured, a command with ``*args`` cannot have sub-commands.

.. code-block:: python

    @Command()
    def foo(first=None, *files, verbose__v=False):
        print(f"first={first!r}  verbose={verbose__v}  files={files}")

.. code-block:: console

    $ ./cli.py foo *
    first='cli.py'  verbose=False  files=('README.rst', ...)

    $ ./cli.py foo - *
    first=None  verbose=False  files=('cli.py', 'README.rst', ...)

In the first example, the first file name is captured by ``first`` and the remaining files would go to ``files``.
In the second example, ``first`` is skipped so all files go to ``files``.  

Both the first and second examples have a tricky corner-case.
If you have a file that starts with a dash *(why!?)*, then it might be treated as a keyword name and accidentally set the ``verbose`` flag, for example.
By explicitly ending the keyword section with ``--`` you can safely capture any weirdly-named files.

.. code-block:: console

    $ ./cli.py foo hello -vv -- *
    first='hello'  verbose=2  files=('cli.py', '--verbose', ...)

If your command does not take any keyword parameters (or ``**kwargs``) then this is not an issue.

If your var-args parameter name starts with an underscore (e.g., ``*_args``), then it is considered :ref:`hidden <hidden-params>` and will not capture additional command-line arguments.
However, extra positional arguments may still be passed programmatically when calling the sub-command (e.g., ``_sub_cmd(1,2,3)``).


\**kwargs
----------

Arbitrary keyword arguments may be collected.
Values are typed as ``str`` by default, unless they appear in a `:ref:flag group <bool-type>`, in which case they are typed as ``bool``.

A double dash ``--`` can be used to force the end of the current command's argument parsing.

.. code-block:: python

    @Command()
    def foo(a=False, **kwargs):
        print(f"a={a}  kwargs={kwargs}")

.. code-block:: console

    $ ./cli.py foo -axd 33 --long-name hi,bye
    a=True  kwargs={'x':True, 'd':'33', 'long_name':'hi,bye'}



Edge Cases / Quirks
====================

This section highlights some of the rarely encountered edge cases and quirks.


.. _backslash:

Backslash Escape
------------------

In order to pass an argument value that starts with a dash (e.g., ``-not-a-keyword``) you must escape the initial dash with a backslash.

**Note**: Values that do not look like keywords (e.g., negative numbers) do not need to be escaped.

.. code-block:: python

    @Command()
    def foo(x:list, y:int):
        print(f"x={x}  y={y}")

**Note**: The shell eats one backslash if you don't surround the argument in quotes.

.. code-block:: console

    $ ./cli.py foo \\-y -9 \\- -y -3
    x=['-y', '-9', '-']  y=-3

For consistency, a single leading backslash is removed from any value during parsing.
The exception is arguments captured as :ref:`*args <var-args>` are kept as-is without leading backslashes getting removed.

.. code-block:: console

    $ ./cli.py foo \\\\hi \\ -y \\33
    x=['\\hi', '']  y=33

Notice the argument with a single backslash ``\\`` becomes an empty string after the leading backslash is removed.

.. _hidden-params:

Hidden Parameters
------------------

A single, leading underscore on a parameter marks it as 'hidden'.
This means it will not be settable with command-line arguments, and it is not visible in generated documentation.
Such parameters are only usable programmatically.
This also applies to :ref:`*args and **kwargs <var-args>` parameters.

.. code-block:: python
    
    @Command()
    def bar(_private, /, q, **_kwargs):
        print(f"bar: private={_private}  q={q}  kwargs={_kwargs}")

    @Command(bar)
    def foo(_x=1, y=2, _z=3, t=4, _sub_cmd):
        print(f"foo: x={_x}  y={y}  z={_z}  t={t}")
        _sub_cmd(10, r=11)

.. code-block:: console

    $ ./cli.py foo 6 7 bar
    foo: x=1  y=6  z=3  t=7
    bar: private=10  q=10  kwargs={'r':11}

    $ ./cli.py foo bar -r 11
    Unknown keyword argument 'r'



Trailing Underscore
--------------------

By adding a single trailing underscore to your command name or parameter name, you can alias Python keywords.

.. code-block:: python

    @Command()
    def break_(if_, else_):
        print(f"if={if_}  else={else_}")

.. code-block:: console

    $ ./cli.py break --if=cookie --else=fix
    if='cookie'  else='fix'



Skip Argument
--------------

As stated in the section on :ref:`lists <list-type>`, a single dash ``-`` ends the processing of that list and moves to the next parameter.

More generally, a single dash skips that parameter, even if it is not a ``list``

.. code-block:: python

    @Command()
    def foo(x=1, y=[2,3]):
        print(f"x={x}  y={y}")
    
.. code-block:: console

    $ ./cli.py foo - 4 5 6
    x=1  y=[4, 5, 6]

In the same way that a single dash ends the current parameter, a double dash ``--`` ends the current command and starts parsing the next sub-command.

Note that since a single dash skips the current parameter, it is not possible to set an empty list to override the default.
There is no syntax for explicitly setting a list parameter to an empty list from the command-line.

.. code-block:: console
    
    $ ./cli.py foo - -
    x=1  y=[2,3]

    $ ./cli.py foo -y -
    x=1  y=[2,3]


Class Documentation
====================

.. autoclass:: libclipy.core.command.dfn.CommandDfn
.. autoclass:: libclipy.core.command.command.Command
    :members: __call__, __new__, each, wait, each_async