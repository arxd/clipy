from cli import Command, ConfigVar, project_root
from libclipy.core.pretty import CLR

codes = ConfigVar('codes The definition of different workflow codes and their files')

@Command()
def workflow(code='', /, *, list__l=False):
    ''' Edit vscode settings to hide visually distracting files.

    Parameters:
        <code_str>
            This is a string of code characters for different workflows.
            Run with `-l` to list all codes.
            
            Use 'a' for all workflow codes.

            If no code is given then vscode settings are cleared and all files are shown.
    '''
    import json, os
    settings_path = project_root/'.vscode'/'settings.json'
    show_files = []
    if list__l:
        for c, v in codes.v.items():
            print(f"{CLR.y}{c}{CLR.x} {v[0]}")
        return
    for c, v in codes.v.items():
        if 'a' in code or c in code: show_files += v[1]
# Get the settings
    try:
        settings = json.loads(settings_path.read_text(encoding='utf8'))
    except FileNotFoundError:
        settings = {}
    if 'files.exclude' in settings: del settings['files.exclude']
# 
    exclude = [(f,True) for f in os.listdir(project_root)] + [(f,False) for f in show_files]
    if code:
        exclude.append(('.*',True))
        exclude.append(('**/__pycache__', True))
        exclude.append(('**/.pytest_cache', True))
        settings['files.exclude'] = dict(exclude)
# Save
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf8')



@Command()
def venv():
    ''' Setup/clean python environments

    FIXME clean out old venv cruft from .python and info.json
    FIMXE ability to clean out lockfile info from info.json for package upgrade
    '''
    from libclipy.core.venv import Venv
    for venv in Venv.all(): venv.venv_path()
    
    