from cli import Command, ConfigVar
from libclipy.core.pretty import CLR

codes = ConfigVar('workflow_codes The definition of different workflow codes and their files')

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
    show_files = []
    if list__l:
        for c, v in codes.v.items():
            print(f"{CLR.y}{c}{CLR.x} {v[0]}")
        return
    for c, v in codes.v.items():
        if 'a' in code or c in code: show_files += v[1]
# Get the settings
    try:
        with open('.vscode/settings.json') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    if 'files.exclude' in settings: del settings['files.exclude']
# 
    exclude = [(f,True) for f in os.listdir('.')] + [(f,False) for f in show_files]
    if code:
        exclude.append(('.*',True))
        exclude.append(('**/__pycache__', True))
        exclude.append(('**/.pytest_cache', True))
        settings['files.exclude'] = dict(exclude)
# Save
    os.makedirs('.vscode', exist_ok=True)
    with open('.vscode/settings.json', 'w') as f:
        json.dump(settings, f, indent=2)

