from collections import namedtuple

SEP = '89rbjw7HmBLE6KQfHKb9xNCw0lfyBkbwTc+DcCQM'
EOL = 'ww+TSrnS3+mg5ogO4AdNjr7iCAUktezuHg77Lfwi'
GitLog = namedtuple('GitLog', ('hash', 'short_hash', 'parent_hash', 'author_name', 'timestamp', 'body','subject', 'refs'))
GitRef = namedtuple('GitRef', ('name', 'short', 'type', 'size', 'hash', 'kind', 'refid'))


class Git():
    sub_cmds = ['config', 'fetch', 'symbolic_ref', 'rev_parse', 'for_each_ref', 'ls_files', 'pull', 'commit', 'add', 'rm', 'checkout', 'push']
    def __init__(self, repo='.'):
        self.repo = os.path.abspath(repo)


    def name(self):
        if not hasattr(self, '_name'):
            l = (self.config('--get', 'remote.origin.url', if_0='utf8,null,', msg=None, or_else=',null,') or '').strip()
            if not l: l = self.rev_parse('--show-toplevel', if_0='utf8,,', msg=None).strip()
            self._name = os.path.splitext(os.path.basename(l))[0]
        return self._name


    def status(self, changes_only=False):
        changes = [x for x in self('status', '-z', if_0='utf8,,', msg=None).split('\0') if x]
        changes = [(k[:2],k[3:]) for k in changes]
        if changes or changes_only: return changes
        if self.fetch('--dry-run', if_0='utf8,,', msg=None).strip():
            return [('  ','Need to pull')]
        if self('status', '-sb', if_0='utf8,,', msg=None).splitlines()[0].split('[')[-1].startswith('ahead'):
            return [('  ','Need to push')] 
        return []


    def head_sym(self, short=False):
        args = (['--short'] if short else []) + ['HEAD']
        return (self.symbolic_ref(*args, msg=None, if_0='utf8,null,', or_else=',null,') or '').strip()


    def head_commit(self):
        return self.rev_parse('HEAD', if_0='utf8,,', msg=None).strip()


    def log(self, commit_hash):
        pretty = f'%H{SEP}%h{SEP}%P{SEP}%an{SEP}%at{SEP}%b{SEP}%s{SEP}%D{EOL}'
        s = self('log', commit_hash, f"--pretty=format:{pretty}", if_0='utf8,,', msg=None)
        for line in s.split(EOL):
            line = line.lstrip()
            if not line: continue
            log = GitLog(*line.split(SEP))
            refs = [r.strip() for r in log.refs.split(',') if r]
            for i, ref in enumerate(refs):
                if not ref.startswith('HEAD'): continue
                s = ref.split(' -> ')
                if len(s) == 2:
                    refs[i:i+1] = s
                else:
                    refs.append(refs.pop(i))
                break
            yield log._replace(refs=refs)


    def refs(self):
        format = f'%(refname){SEP}%(refname:short){SEP}%(objecttype){SEP}%(objectsize){SEP}%(objectname){EOL}'
        data = self.for_each_ref(f'--format={format}', msg=None, if_0='utf8,,')
        refid = 0
        for line in data.split(EOL):
            if not line.lstrip(): continue
            parts = list(line.lstrip().split(SEP))
            parts[3] = int(parts[3])
            parts.append('unk')
            if parts[0].startswith('refs/heads/'): parts[-1] = 'branch'
            if parts[0].startswith('refs/remotes/'): parts[-1] = 'remote'
            parts.append(refid)
            refid += 1
            yield GitRef(*parts)
        yield GitRef('HEAD', 'HEAD', 'symref', 0, self.head_sym() or self.head_commit(), 'HEAD', refid)


    def up_to_date(self):
        return not bool(self.status())


    def ls(self, *pattern, invert=False):
        return self.ls_files(*(list(pattern) + (['--other'] if invert else [])), msg=None, if_0='utf8,,').splitlines()


    def pull_rebase(self, *args, **kwargs):
        self.pull('--rebase', *args, **kwargs)


    def is_worktree_dirty(self):
        for status, path in self.status():
            if status != '??': return True


    def create_orphan_branch(self, name, gitignore=[], remote='origin'):
        cur = self.head_sym(short=True)
        if not cur: raise UsageError(f"Head is detached")
        if self.is_worktree_dirty():
            raise UsageError(f'Git worktree is not clean.  Commit changes and try again.')
        self.checkout('--orphan', name)
        self.rm('-rf', '.')
        with open(f'.gitignore', 'w') as f:
            f.write('\n'.join(gitignore))
        self.add('.gitignore')
        self.commit('-m', f'{name} orphan branch')
        self.push('-u', remote, name)
        self.checkout(cur)
        return f'{remote}/{name}'


    def __call__(self, *args, **kwargs):
        return run(['git', '-C', self.repo, *args], **kwargs)


    def __getattr__(self, cmd):
        if cmd not in self.sub_cmds: return super().__getattr__(cmd)
        return partial(self, cmd.replace('_','-'))


    def __str__(self):
        return self.repo


import os
from functools import partial
from .run import run, UsageError
