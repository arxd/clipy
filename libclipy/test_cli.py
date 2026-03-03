import os, sys, json

# We want to run the coverage and pytest in a separate process so that it has a clean environment to see all imports
if __name__ == '__main__':
    import coverage, pytest
    sys.path[0] = os.getcwd()
    args = json.loads(sys.argv[1])
    #from pyutil.core.cli_util import ClipyLogger, ClipyLogFilter
    #logging.setLoggerClass(ClipyLogger)
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
    cov.html_report(directory="local/coverage")
    cov.xml_report(outfile="local/coverage/coverage.xml")
    sys.exit(0)


from libclipy import CLI, pip

@CLI(need=pip('pytest coverage pytest-asyncio pytest-timeout'))
def test(spec=None, /, *, verbose__v=False, coverage__c=False):
    ''' Run all unit tests

    Parameters:
        <spec>
            The first parameter to pytest.
            e.g. some_dir/file.py::test_name
        --verbose, -v
            verbose output
        --coverage, -c
            Open coverage data in the browser
    '''
    from functools import reduce
    args = [['libclipy']]
    args += reduce(lambda a,b:a+b, [['--ignore', x] for x in os.listdir('.') if os.path.isdir(x) and x not in args[0]])
    pytest_ini = dict(
        asyncio_mode = 'strict', # auto
        timeout = 2,
        python_files='_test_*.py',
        asyncio_default_fixture_loop_scope='function',
        log_format = '%(lvl)s %(message)s%(names)s %(rloc)s%(obj)s',
    )
    for k,v in pytest_ini.items(): args += ['-o', f'{k}={v}']
    if verbose__v: args.append('-'+'v'*int(verbose__v))
    args.append('--capture=fd')
    args.append(f"--show-capture={'all' if verbose__v else 'log'}")
    args.append('--maxfail=1')
    if spec: args.append(spec)
# run pytest.main in a separate process (Because it needs it's own event loop and a clean module load)
    from libclipy.setup import run
    if (r:=run([sys.executable, 'libclipy/test_cli.py', json.dumps(args)])): sys.exit(r)
    if coverage__c:
        url = 'local/coverage/index.html'
        try: run(['open', '-a', 'Google Chrome', url])
        except:
            try: run(['open', '-a', 'Safari', url])
            except:
                import webbrowser
                webbrowser.open(url, new=2)

