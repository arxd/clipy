from libclipy import CLI, pip
from pathlib import Path

DIST = Path('docs/_dist')



@CLI
def view(section__s='', *, local__l=False):
    ''' Open the html documentation in the browser.

    Parameters:
        <str>, --section <str>, -s <str>
            Jump straight to a subsection of the documentation
        --local, -l
            Don't pull, only view local documentation 
    '''
    ensure_docs()
    if not local__l: Git(DIST).pull('--rebase')
    section = find_section(section__s)
    if not section: raise UsageError(f"No documentation available to view.  You need to build it:\n  $ ./cli.py docs build")
        #build()
        #section = find_section(section__s)
        #assert(section), f"No documentation available to view.  You need to build it:\n  $ ./cli.py docs build"
    url = 'file://' + section
    print.ln(f'Opening documentation in the browser~lang ja~ブラウザでドキュメントを開く', '...', ['']*2, url)
    try: run(['open', '-a', 'Google Chrome', url])
    except:
        try: run(['open', '-a', 'Safari', url])
        except:
            import webbrowser
            webbrowser.open(url, new=2)


@CLI(need=pip('sphinx-rtd-theme sphinxcontrib-mermaid sphinx-markdown-builder myst-parser Pygments'))
def build():
    ''' Build the documentation.
    '''
    env_bin = os.path.split(sys.executable)[0]
    ensure_docs()
    #cfg = Config()
    shutil.rmtree('docs/gen', ignore_errors=True)
    #cli_gen('docs/gen/cli')
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = 'x'
    env['VERSION'] = f'0.1'
    env['SERVICE_NAME'] = 'cfg.name'
    shutil.rmtree(DIST/'html', ignore_errors=True)
    run([f"{env_bin}/sphinx-build", '-a', '-b', 'html', '-c', 'docs', '.', DIST/'html'], env=env)
    shutil.rmtree(DIST/'markdown', ignore_errors=True)
    run([f"{env_bin}/sphinx-build", '-a', '-b', 'markdown', '-c', 'docs', '.', DIST/'markdown'], env=env)
    


@CLI
def push():
    ''' Overwrite the remote documentation with the current built documentation.
    '''
    repo = Git(DIST)
    repo.add('-A')
    repo.commit('--amend', '-m', 'cli.py docs')
    repo.push('--force')

    

def find_section(section):
    docs = os.path.realpath(DIST/'html')
    options = set()
    for base, dirs, files in os.walk(docs):
        for f in files:
            option = os.path.splitext(f.lower())[0]
            options.add(option)
            if option == section.lower():
                return os.path.join(base, f)
    if section: raise UsageError(f"Section must be one of: {' '.join(options)}")
    fname = os.path.join(docs, 'README.html')
    return fname if os.path.exists(fname) else ''



def ensure_docs():
    ''' Make sure the basic documentation structure is in place
    '''
    if DIST.is_dir(): return
# Find remote docs branch or create a new orphan branch
    repo = Git()
    try:
        repo.worktree('add', DIST, 'docs', '-f')
    except:
        print.ln(f"Creating docs branch")
        gitignore = '* !/html/ !/html/** !/markdown/ !/markdown/** !.gitignore'.split(' ')
        repo.create_orphan_branch('docs', gitignore, remote='origin')
        repo.worktree('add', DIST, 'docs')
    



def cli_gen(outfolder):
    os.makedirs(outfolder, exist_ok=True)
    main = CLI.main()
    print.ln("Generate cli.py documentation~lang ja~cli.pyドキュメントを生成する")
    create_file(main, outfolder, prefix=[main.name])



def write_cmd(cmd, f, prefix=[]):
    if not cmd.sub_module_paths: f.write(f".. _{'_'.join(prefix)}:\n\n")
    f.write(f"{cmd.name.replace('_','-')}\n{'-'*len(cmd.name)}\n\n")
    cmd.doc().print(-1, stream=f)
    if cmd.sub_module_paths:
        f.write(f".. toctree::\n   :maxdepth: 1\n\n   {'_'.join(prefix)}\n\n")
        f.write('.. list-table::\n   :widths: 1 100\n\n')
        for sub in cmd.sub_commands().values():
            f.write(f"   * - :ref:`{'_'.join(prefix)}_{sub.name}`\n")
            f.write(f"     - " + str(sub.doc().subs[0].text) + '\n')
        f.write('\n')
        #f.write(f".. toctree::\n   :maxdepth: 2\n\n   {'_'.join(prefix)}\n\n")




def create_file(cmd, outfolder, prefix=[]):
    print(f"  {'_'.join(prefix)}.rst")
    with open(os.path.join(outfolder,f"{'_'.join(prefix)}.rst"), 'w') as f:
        f.write(f".. _{'_'.join(prefix)}:\n\n")
        f.write(f"{'#'*len(cmd.name)}\n{cmd.name.replace('_','-')}\n{'#'*len(cmd.name)}\n\n")
        cmd.doc().print(-1, stream=f)
        f.write(".. contents::\n   :local:\n\n")
        subs = cmd.sub_commands()
        for name in sorted(subs):
            write_cmd(subs[name], f, prefix + [name])
            if subs[name].sub_module_paths: create_file(subs[name], outfolder, prefix + [name])



@CLI(build, view, push)
def docs():
    ''' View/build documentation
    '''


import os, sys, shutil
#from config import Config
from libclipy.tools.run import run, UsageError
from libclipy.tools.git import Git
from libclipy import print
