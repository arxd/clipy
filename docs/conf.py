import os, sys
sys.path[0:0] = [os.path.abspath(x) for x in ['..', '../scripts/core/docs/ext']]
#from config import Config
#cfg = Config()
project = 'cfg.name'
release = 'cfg.version'
default_role = 'any'
extensions = ['sphinx.ext.viewcode', 'sphinx.ext.autosummary', 'sphinx.ext.napoleon', 'myst_parser', 'sphinx.ext.autodoc', 'sphinxcontrib.mermaid', 'sphinx_markdown_builder']#, 'markdown_mermaid']
inc = {'README.rst', 'docs'}
exclude_patterns = list(set(os.listdir('..')).difference(inc)) + ['docs/_*']
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_favicon = '_static/favicon.png'
master_doc = 'README'
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}
