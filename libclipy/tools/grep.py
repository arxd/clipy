from .. import CLI
from .git import Git
import re

@CLI.cmd()
def grep(pattern, *, case__c=False, group__g=[]):
    ''' Grep all relevant files (and filenames) in the project for regex <pattern>

    Parameters:
        <str>, --pattern <str>
            A regex pattern to search for
        --case, -c
            Case sensitive search
        --group [grp], -g [grp]
            Only show matches in specific groups

    Example:
        ./cli.py grep FIXME
    '''
    grep_groups = {k:re.compile(v) for k,v in CLI.cfg('grep_groups').items()}
    show_groups = group__g or (['other'] + list(grep_groups.keys()))
# Group matches into groups
    matches = {}
    for line in Git().grep(pattern, *(['--no-ignore-case'] if case__c else [])):
        for grp in grep_groups:
            if grep_groups[grp].match(line[0]): break
        else:
            grp = 'other'
        if grp not in show_groups: continue
        matches.setdefault(grp, [])
        matches[grp].append( (f"{line[0]}:{line[1]}", line[2]))
# Show by group
    showed = False
    for grp in show_groups:
        if not matches.get(grp,[]): continue
        showed = True
        print('\n',grp)
        print('-'*80)
        w = max(0,0,*[len(m[0]) for m in matches[grp]])
        for loc, txt in matches.get(grp,[]):
            print(f"{loc}{' '*(w-len(loc))}  {txt.lstrip()}")
#
    print('')
    if not showed: print("No matches found")
