# The syntax of this file must be python2 compatible

import sys, re, os


def ensure_environment(need, venv):
    ''' Ensure the execution evironment is what our project needs.
    
    It ensures the currently running version of python matches the `need` regular expression.
    If it doesn't match it attempts to install a compatable version using ``pyenv``.

    Next it makes sure we are running in the given `venv`.
    If `venv` is None then we are fine using the system python and nothing is done.
    Otherwise it creates the `venv` if it doesn't exist and changes to that python executable.
    '''
# Change to the directory containing cli.py so that our commands always know they are in the project root
    project_root = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
    os.chdir(project_root)
    if not os.path.exists('local'): os.makedirs('local')
# Check that we are running a good python version
    need_re = re.compile(need+'$')
    have = "%s.%s.%s"%sys.version_info[:3]
    if need_re.match(have): return _ensure_venv(project_root, venv)
# Nope, we aren't compatable
    print("Incompatible Python version\n")
    print("Have: \x1b[0;31m%s\x1b[0m"%have)
    print("Need: \x1b[0;33m%s\x1b[0m\n"%need)
# Try to install a good version using pyenv
    have = run(['pyenv', 'versions', '--bare'], capture=True)
    if have == None:
        _exit(50, "Try installing pyenv to manage different python versions.\nhttps://github.com/pyenv/pyenv?tab=readme-ov-file#installation")
    version = _latest([v.strip() for v in have.split('\n') if need_re.match(v.strip())])
    if not version:
    # The user does not have a compatible version installed
        version = _latest([v.strip() for v in run(['pyenv', 'install', '--list'], capture=True).split('\n') if need_re.match(v.strip())])
        if not version or run(['pyenv', 'install', version]) != 0:
            _exit(51, "You need to manually install a compatable python version.")
# Set the new version locally for the project
    run(['pyenv', 'local', version])
    print("Installed compatible python version: \x1b[0;33m%s\x1b[0m"%version)
    os.execv('%s/bin/python'%run(['pyenv','prefix',version], capture=True).strip(), ['python'] + sys.argv)



def ensure_packages(*packages):
    ''' Uses pip to ensure that the packages are installed, but only if we are in a venv.
    '''
    packages = sorted([p.strip() for pkg in packages for p in pkg.split(' ') if p.strip()])
    project_root = os.path.dirname(os.path.abspath(sys.modules.get('__main__').__file__))
    if not sys.executable.startswith(project_root): return
    venv = os.path.split(os.path.split(sys.executable)[0])[0]
# Look at what packages have already been installed in this directory
    with open('%s/packages.txt'%venv) as f: have = set([p for p in f.read().split('\n') if p.strip()])
    missing = set(packages) - have
    if not missing: return
    print("Install: %s to %s"%(missing, venv))
    if run(['%s/bin/python'%venv, '-m', 'pip', 'install', *missing]) != 0: _exit(55, "Failed to install all packages")
    with open('%s/packages.txt'%venv, 'w') as f:
        f.write('\n'.join(have | missing))



def _ensure_venv(project_root, venv):
    if venv == None: return
    venv = '%s/.python/%s'%(project_root,venv)
    if sys.executable == '%s/bin/python'%venv: return
# Ensure that the venv exists and execv to its python
    if not os.path.exists(venv):
        print("Create new venv: \x1b[0;33m%s\x1b[0m"%venv)
        if run([sys.executable, '-m', 'venv', venv]) != 0: _exit(57, "Failed to create venv")
        with open('%s/packages.txt'%venv, 'w'): pass
        if run(['%s/bin/python'%venv, '-m', 'pip', 'install', '-U', 'pip', 'wheel', 'setuptools', 'wcwidth']) != 0: _exit(58, "Failed to upgrade pip")
    os.execv('%s/bin/python'%venv, ['python'] + sys.argv)



def _exit(code, msg):
    print("\x1b[0;31m%s\x1b[0m\n"%msg)
    sys.exit(code)



def run(cmd, capture=False, or_else=None):
    import subprocess
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE if capture else None)
        resp = (proc.communicate()[0] or b'').decode('utf8').strip()
        return resp if capture else proc.returncode
    except Exception as e:
        return or_else



def _to_int(s):
    try:
        return int(s)
    except:
        return 0



def _latest(versions):
    if not versions: return None
    return sorted(versions, key=lambda x: tuple(map(_to_int, x.split('.'))), reverse=True)[0]
