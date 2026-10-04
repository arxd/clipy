import os, sys, json


# We want to run the coverage and pytest in a separate process so that it has a clean environment to see all imports
if __name__ == '__main__':
    import coverage, pytest, logging
    sys.path.insert(0, sys.argv[1])
    os.chdir(sys.path[0])
    args = json.loads(sys.argv[2])
    from libclipy.core.logger import ClipyLogger
    logging.setLoggerClass(ClipyLogger)

    cov = coverage.Coverage(branch=True, source=args.pop(0), omit=[
        "_test*.py",
        "__init__.py",
    ],)
    cov.start()
    code = pytest.main(args)
    cov.stop()
    if code: sys.exit(code)
    cov.save()
    #cov.report(show_missing=True)
    cov.html_report(directory="local/coverage") # FIXME change to work_root  (need to pass it through sys.apth)
    cov.xml_report(outfile="local/coverage/coverage.xml")
    sys.exit(0)



from cli import Command, Cmd, Venv, project_root

@Venv('cli::main', req='pytest coverage pytest-asyncio pytest-timeout')
@Command()
def test(spec=None, /, *, coverage__c=False, keep_going__k=False):
    ''' Run all unit tests

    Parameters:
        <spec>
            The first parameter to pytest.
            e.g. some_dir/file.py::test_name
        --coverage -c
            Open coverage data in the browser
        --keep-going -k
            Don't stop at the first error
    '''
    from functools import reduce
    from libclipy.core.config import verbosity
    args = [['libclipy']]
    args += reduce(lambda a,b:a+b, [['--ignore', x] for x in os.listdir('.') if os.path.isdir(x) and x not in args[0]])
    pytest_ini = dict(
        asyncio_mode = 'strict', # auto
        timeout = 5,
        python_files='_test_*.py',
        asyncio_default_fixture_loop_scope='function',
        log_format = '%(lvl)s %(message)s%(names)s %(rloc)s%(obj)s',
    )
    for k,v in pytest_ini.items(): args += ['-o', f'{k}={v}']
    if verbosity.v > 0: args.append('-'+'v'*verbosity.v)
    args.append('--capture=fd')
    args.append(f"--show-capture={'all' if verbosity.v > 0 else 'log'}")
    if not keep_going__k: args.append('--maxfail=1')
    args.append('--import-mode=importlib')
    if spec: args.append(spec)
# run pytest.main in a separate process (Because it needs it's own event loop and a clean module load)
    Cmd(sys.executable, '-I', 'libclipy/cli_testing.py', project_root, json.dumps(args)).on(0).call(',,raise')
    if coverage__c:
        url = 'local/coverage/index.html'
        Cmd('open', '-a', 'Google Chrome', url).call(',,raise')
        Cmd('open', '-a', 'Safari', url).call(',,raise')
        import webbrowser
        webbrowser.open(url, new=2)

