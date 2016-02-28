#!/usr/bin/env python
# coding: utf-8

import os

# tox is usually installed in python2 environment, so it's better
# to maintain python2 compatibility in setup.py
from io import open
from setuptools import setup, find_packages

from xsnippet_api import __version__ as version
from xsnippet_api import __license__ as license


here = os.path.dirname(__file__)
with open(os.path.join(here, 'README.rst'), 'r', encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='xsnippet_api',
    version=version,

    description='XSnippet is a simple web-service for code snippets sharing.',
    long_description=long_description,
    license=license,
    url='http://github.com/xsnippet/xsnippet-api/',
    keywords='web-service restful-api snippet storage',

    author='The XSnippet Team',
    author_email='dev@xsnippet.org',

    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    zip_safe=False,

    setup_requires=[
        'pytest-runner',
    ],

    install_requires=[
        'aiohttp >= 0.21.2',
        'motor >= 0.5',
        'werkzeug >= 0.11.4',
    ],

    tests_require=[
        'pytest >= 2.8.7',
    ],

    entry_points={
        'console_scripts': [
            'xsnippet-api = xsnippet_api.__main__:main',
        ],
    },

    classifiers=[
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',

        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',

        'Topic :: Internet :: WWW/HTTP',

        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
)