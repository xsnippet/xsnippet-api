import os
import pkg_resources


here = os.path.abspath(os.path.dirname(__file__))

project = 'XSnippet API'
copyright = '2017, The XSnippet Team'
release = pkg_resources.get_distribution('xsnippet-api').version
version = '.'.join(release.split('.')[:2])
extensions = [
    'sphinxcontrib.redoc',
]
source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
redoc = [
    {
        'name': project,
        'page': 'api/index',
        'spec': os.path.join(here, '..', 'contrib', 'openapi', 'spec.yml'),
    },
]

if not os.environ.get('READTHEDOCS') == 'True':
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
