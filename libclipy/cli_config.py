from cli import Command, ConfigVar

@Command()
def config(*vars):
    ''' Show the given config vars.
    
    If none are given then show all config vars in config.py
    '''
    import config, cli
    cli_vars = ['name', 'version', 'project_root', 'env_prefix']
    if not vars: vars = [k for k in dir(config) if isinstance(getattr(config, k), ConfigVar)] + cli_vars
    return {k:getattr(cli, k) if k in cli_vars else ConfigVar.get_by_name(k).export() for k in vars}
