import os
from cli import Command

@Command()
def hide(code=''):
    ''' Edit vscode settings to hide visually distracting files.

    Parameters:
        <code_str>, --code <code_str>
            This is a string of code characters that correspond to groups of files/folders

    Examples:
        ./cli.py hide a
    '''
    import json

    files = ['libclipy', 'docs', 'local', 'cli.py', 'README.rst', 'README.rst.tmpl']
# Get the settings
    try:
        with open('.vscode/settings.json') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    if 'files.exclude' in settings: del settings['files.exclude']
# 
    exclude = [(f,True) for f in os.listdir('.')] + [(f,False) for f in files]
    if code:
        exclude.append(('.*',True))
        exclude.append(('**/__pycache__', True))
        exclude.append(('**/.pytest_cache', True))
        settings['files.exclude'] = dict(exclude)
# Save
    os.makedirs('.vscode', exist_ok=True)
    with open('.vscode/settings.json', 'w') as f:
        json.dump(settings, f, indent=2)

