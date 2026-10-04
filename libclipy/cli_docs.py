import os, sys, shutil
from pathlib import Path
from cli import Cmd, Command, Venv, UsageError
from libclipy.core.errors import CmdError
from libclipy.tools.git import Git


DIST = Path('docs/_dist')


@Command('.cli_docs')
def docs():
    ''' View/build documentation
    '''


@Command()
def view(section__s='', *, local__l=False):
    ''' Open the html documentation in the browser.

    Parameters:
        <str>, --section <str>, -s <str>
            Jump straight to a subsection of the documentation
        --local, -l
            Don't pull, only view local documentation 
    '''
    ensure_docs()
    if not local__l:
        try:
            Git(repo=DIST).pull('--rebase').call()
        except:
            print(f"Couldn't pull remote documentation.  Using local docs")
    section = find_section(section__s)
    if not section:
        raise UsageError(f"No documentation available to view.  You need to build it:\n  $ ./cli.py docs build")
        #build()
        #section = find_section(section__s)
        #assert(section), f"No documentation available to view.  You need to build it:\n  $ ./cli.py docs build"
    url = 'file://' + section
    print(f'Opening documentation in the browser~lang ja~ブラウザでドキュメントを開く', '...', ['']*2, url)
    try:
        Cmd('open', '-a', 'Google Chrome', url).call(',,raise')
        Cmd('open', '-a', 'Safari', url).call(',,raise')
        import webbrowser
        webbrowser.open(url, new=2)
    except CmdError: pass


@Venv(req='sphinx-rtd-theme sphinxcontrib-mermaid sphinx-markdown-builder myst-parser Pygments')
@Command()
async def build(*, html=False):
    ''' Build the documentation.

    Parameters:
        --html
            Build html only
    '''
    from cli import name, version, project_root
    ensure_docs()
    shutil.rmtree('docs/gen', ignore_errors=True)
    shutil.rmtree(DIST/'html', ignore_errors=True)
    shutil.rmtree(DIST/'markdown', ignore_errors=True)
    #cli_gen('docs/gen/cli')
    sphinx = Cmd(build.bin_path/'sphinx-build', '-a', '-c', 'docs')
    sphinx.env(PYTHONDONTWRITEBYTECODE='x', VERSION=version, SERVICE_NAME=name, CLIPY_ROOT=project_root)
    import asyncio
    coro = [sphinx('-b', 'html', '.', DIST/'html').call_async()]
    if not html: coro.append(sphinx('-b', 'markdown', '.', DIST/'markdown').call_async())
    group = asyncio.gather(*coro)
    try:
        await group
    finally:
        group.cancel()
        await group



@Command()
def push():
    ''' Overwrite the remote documentation with the current built documentation.
    '''
    repo = Git(repo=DIST)
    repo.add('-A').say().call()
    repo.commit('--amend', '-m', 'cli.py docs').say().call()
    repo.push('--force').say().call()

    

def find_section(section):
    docs = DIST/'html'
    options = set()
    for base, dirs, files in os.walk(docs):
        for f in files:
            option = os.path.splitext(f.lower())[0]
            options.add(option)
            if option == section.lower():
                return os.path.join(base, f)
    if section: raise UsageError(f"Section must be one of: {' '.join(options)}")
    return fname if (fname := docs/'README.html').exists() else ''



def ensure_docs():
    ''' Make sure the basic documentation structure is in place
    '''
    if DIST.is_dir(): return
# Find remote docs branch or create a new orphan branch
    repo = Git()
    try:
        repo.worktree('add', DIST, 'docs', '-f').say().call()
    except:
        print(f"Creating docs branch")
        gitignore = '* !/html/ !/html/** !/markdown/ !/markdown/** !.gitignore'.split(' ')
        repo.create_orphan_branch('docs', gitignore, remote='origin').say().call()
        repo.worktree('add', DIST, 'docs').say().call()
    

'''
def cli_gen(outfolder):
    os.makedirs(outfolder, exist_ok=True)
    main = CLI.main()
    print("Generate cli.py documentation~lang ja~cli.pyドキュメントを生成する")
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
'''
