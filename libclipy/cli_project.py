from cli import Command, run
from libclipy.core.pretty import CLR, print as pprint
from .project import Project
from libclipy.tools.diff import Diff
from config import version


@Command()
def new_(project_path, feature__f=[]):
    ''' Create a new project

    Parameters:
        <project_path>
            A path to the new project root
        --feature -f <feature_name>*
            We need this clipy feature
    '''
    from config import version
    from libclipy.tools.sed import Sed
    clipy = Project()
    proj = Project(project_path)
    if proj.git.repo.exists(): raise ValueError(f"Project already exists: {proj}")
    features = list(set(['cli.grep','cli.workflow']) | set(feature__f))
    clipy.verify_features(features)
    files = clipy.files(*features)
# Copy files
    proj.git.repo.mkdir()
    for f in files: clipy.copy_to(f, proj)
    for f in ['README.rst.tmpl', 'config.py', '.gitignore']: clipy.copy_to(f, proj)
# Edit files
    name = proj.git.repo.name
    sed = Sed()
    sed.sub(proj.file('config.py'), f"s/name = .*/name = '{name}'/", f"s/'core.*libclipy'/'libclipy'/", f"s/version = .*/version = '0.0.1'/")
    sed.sub(proj.file('README.rst'), f"1s/.*/{'='*(len(name)+1)}/", f'2s/.*/{name.title()}/', f"3s/.*/{'='*(len(name)+1)}/")
    entries = [f"'libclipy.{x.replace('.','_')}', "  for x in features if x.startswith('cli.') or x == 'docs']
    sed.sub(proj.file('cli.py'), f"s/@Command.*/@Command({''.join(entries)}sub_required=False)/")
    proj._info = {'version':version, 'features':features}
    proj.set_info(hashes={str(f):clipy.hash(f) for f in files})
# Init git
    proj.git('init', '-b', 'main')
    proj.git('add', '.')
    proj.git('commit', '-m', 'Boilerplate clipy code')
# Add it to Projects
    Project.lookup(str(proj))



@Command()
def diff(project_name='', verbose__v=False):
    ''' Compare the files in this reference implementation to the files in a derived project
    
    Parameters:
        <project>
            The path to the project to compare against.
            If you give just the project name then the local/projects.json file will be searched to find the path.
    '''
    diff = Diff()
    clipy = Project()
    if project_name:
        proj = Project.lookup(project_name)
        for f, d in proj.diff().items():
            if d.status == 'd':
                print(f" d {CLR.bld}{d.path}{CLR.x} {CLR.r}deprecated{CLR.x}")
                continue
            x = diff.compare(proj.file(f), clipy.file(f), path=f)
            if int(verbose__v) < 2 and x.status == 'same': continue
            if not verbose__v and not d.status: continue
            print(f"{d.status:>2} ")
            pprint.pretty(x)
        print(f"\n{CLR.o} version {CLR.x}: {proj.info.get('version')}")
        print(f"{CLR.o}features {CLR.x}: {proj.info.get('features')}")
        print(f"{CLR.o}    path {CLR.x}: {proj}")
        print(proj.description())
    else:
        for proj in Project.all():
            kinds = {}
            clean = (proj.info['version'] == version)
            for f,d in proj.diff().items():
                clean = clean and not d.status
                kinds[d.status] = kinds.get(d.status, 0) + 1
                x = diff.compare(proj.file(f), clipy.file(f))
                kinds[x.status] = kinds.get(x.status, 0) + 1
            kinds = [f'{k}:{v}' for k,v in kinds.items() if k not in ('', 'same')]
            print(f"{CLR.bld if clean else CLR.r}{proj} {CLR.y}{proj.info.get('version')} {CLR.c}{' '.join(kinds)} {CLR.m}{' '.join(proj.info['features'])}{CLR.x}")
            print(CLR.a, proj.description(), CLR.x)



@Command()
def features(project_name='', *, add__a=[], rem__x=[]):
    ''' Add or remove features from a project.

    Parameters:
        <project>
            The path or name of the project to edit
        --add -a <feature>*
            Add a feature to the project
        --rem -x <feature>*
            Remove a feature from the project
    '''
    proj = Project.lookup(project_name)
    before = set(proj.info['features'])
    after = (before | set(add__a)) - set(rem__x)
    print(proj.info['features'], '->', 'No change' if before == after else after)
    if before == after: return
    Project().verify_features(after)
    proj.set_info(features=list(after))



@Command()
def sync(project_name='', *, force__f=False, reverse__r=False):
    ''' Synchronize a project with the clipy reference.
    
    Parameters:
        <project>
            The path or name of the project to sync.
        --reverse -r
            We want to move changes from the project to clipy.
            This is the reverse of what we are normally doing which is moving changes from clipy to our project.
            Resolve diff conflicts even if only the project's file changed.
        --force -f
            Ignore any previous syncs with this project.
            You will need to re-resolve many conflicting files and missing files will be re-copied.
    '''
    diff = Diff()
    clipy = Project()
    proj = Project.lookup(project_name)
    if force__f: proj.sync_hashes = {}
    diffed = proj.diff()
    for f, d in diffed.items():
        if not d.status: continue
    # delete deprecated files?
        if d.status == 'd':
            print(f"Delete deprecated {CLR.r}{d.path}{CLR.x}?")
            if (pf:=proj.file(f)).exists() and input("[d]elete / keep: ") == 'd':
                pf.unlink()
            continue
    # Do an actual diff of the files
        x = diff.compare(proj.file(f), clipy.file(f), path=f)
        if x.status == 'same': continue
    # Copy over missing files
        if x.status == 'missing':
            if d.proj_hash_cached is None:
                print(f"Copy new file: {f}")
                clipy.copy_to(f, proj)
            else:
                print(f"Project deleted: {f}")
            continue
        # Did only the project's file change?
        if d.status == 'p' and not reverse__r: continue
    # Resolve a changed file
        pprint.pretty(x)
        print(f"Status: {d.status:>2}")
        if (p:=input("[e]dit / [c]opy / keep: ")) == 'c':
            clipy.copy_to(f, proj)
        elif p == 'e':
            run(['vimdiff', proj.file(f), clipy.file(f)])
    # Update the hashes
    proj.set_info(version=version, hashes={f:d.ref_hash for f,d in diffed.items() if d.status != 'd'})
    proj.set_sync_hashes({f:proj.hash(f) for f,d in diffed.items() if d.status != 'd'})
