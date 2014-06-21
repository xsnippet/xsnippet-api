import setuptools


setuptools.setup(
    name='xsnippet',
    version='0.0.1-alpha1',
    packages=setuptools.find_packages(),
    install_requires=[
        'alembic',
        'flask',
        'flask-sqlalchemy',
        'sqlalchemy',
    ],
    author='The XSnippet Team',
    author_email='xsnippet@xsnippet.org',
    description='XSnippet pastebin service',
    license='BSD',
    keywords='pastebin',
    url='http://xsnippet.org',
)
