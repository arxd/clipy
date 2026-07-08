from libclipy import ConfigVar, Command
from libclipy.core.pretty import CLR
from libclipy.tools import Git
import re


clrcode = re.compile('\x1b.*?m')


@ConfigVar()
def grep_groups(v={}):
    ''' The grouping when grepping
    '''
    return {k:re.compile(v) for k,v in v.items()}


@Command()
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
    gg = grep_groups.v
    show_groups = group__g or (['other'] + list(gg.keys()))
# Group matches into groups
    matches = {}
    prev, clr = '', CLR.g
    for line in Git().grep(pattern, '--color=always', *([] if case__c else ['-i'])):
        line = (clrcode.sub('', line[0]), clrcode.sub('',line[1]), line[2])
        for grp in gg:
            if gg[grp].match(line[0]): break
        else:
            grp = 'other'
        if grp not in show_groups: continue
        matches.setdefault(grp, [])
        p = line[0].rsplit('/',1)
        if len(p) == 1: p = ('', p[0])
        if line[0] != prev: prev, clr = line[0], {CLR.b:CLR.g, CLR.g:CLR.b}[clr]
        matches[grp].append( (f"{p[0]}{'/'*bool(p[0])}{clr}{p[1]}{CLR.a}:{line[1]}{CLR.x}", line[2]))
# Show by group
    print('')
    showed = False
    for grp in show_groups:
        if not matches.get(grp,[]): continue
        showed = True
        print(f"\n{CLR.y} {grp}\n{'='*(len(grp)+2)}{CLR.x}")
        w = max(0,0,*[len(m[0]) for m in matches[grp]])
        for loc, txt in matches.get(grp,[]):
            print(f"{loc}{' '*(w-len(loc))}  {txt.lstrip()}")
#
    if not showed: print("No matches found")
    print('')
