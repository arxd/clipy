import pytest

@pytest.mark.skip
def test_docstring_defines_help_output():
    ''' The function docstring should fully define the command documentation shown with -h/--help '''


@pytest.mark.skip
def test_subcommands_discovered_before_execution():
    ''' Sub-commands should be deterministically discovered and parsed before any command executes '''

@pytest.mark.skip
def test_pretty_print_non_none_return():
    ''' If a command returns a non-None value, it should be pretty-printed '''

@pytest.mark.skip
def test_subcommand_chain_parsed_before_execution():
    ''' The full sub-command chain should be parsed before any command executes '''

@pytest.mark.skip
def test_hidden_initial_parameter_receives_subcommand():
    ''' If a command defines a hidden initial positional-only parameter, it should receive the sub-command callable '''

@pytest.mark.skip
def test_return_value_forwarded_to_subcommand():
    ''' If no hidden sub-command parameter is defined, the return value should be forwarded to the sub-command '''

@pytest.mark.skip
def test_subcommand_arguments_override_defaults():
    ''' Command-line arguments to a sub-command should override defaults provided by the parent command '''


# Sub-Command Tests

@pytest.mark.skip
def test_subcommand_module_string_lazy_loaded():
    ''' Passing a module path string to @CLI should lazy-load the module only when the sub-command is invoked '''

@pytest.mark.skip
def test_subcommand_callable_receives_prefix():
    ''' A callable sub-command provider should receive the sub-command prefix string '''

@pytest.mark.skip
def test_subcommand_callable_returns_command_list():
    ''' A callable sub-command provider may return a list of CommandDfn objects '''

@pytest.mark.skip
def test_subcommand_callable_returns_module():
    ''' A callable sub-command provider may return a module or module path containing commands '''


# Generator Tests

@pytest.mark.skip
def test_generator_command_supported():
    ''' Commands defined as generators should yield values as command output '''


@pytest.mark.skip
def test_generator_under_implicit_control_iterated_normally():
    ''' Under implicit control, generator sub-commands should be iterated in the usual way '''


@pytest.mark.skip
def test_generator_under_explicit_control_collected_to_list():
    ''' Under explicit control, generator results should be collected into a list before being returned '''


# *args Tests

@pytest.mark.skip
def test_star_args_disables_subcommands():
    ''' A command defining *args should not allow sub-commands '''


@pytest.mark.skip
def test_double_dash_ends_keyword_section():
    ''' "--" should explicitly terminate keyword parsing to allow dash-prefixed values in *args '''


# Backslash Escape Tests
@pytest.mark.skip
def test_double_leading_backslash_reduces_to_single():
    ''' Double leading backslashes should result in a single literal backslash after parsing '''

@pytest.mark.skip
def test_star_args_preserve_leading_backslash():
    ''' Arguments captured by *args should preserve leading backslashes without removal '''


@pytest.mark.skip
def test_trailing_underscore_allows_python_keyword_name():
    ''' A trailing underscore in a command name should allow aliasing of Python keywords '''

