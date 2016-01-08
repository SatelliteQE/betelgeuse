#!/usr/bin/env python
# coding=utf-8
"""A setuptools-based script for installing Betelgeuse."""
from setuptools import setup

with open('README.rst') as handle:
    LONG_DESCRIPTION = handle.read()

with open('VERSION') as handle:
    VERSION = handle.read().strip()

setup(
    name='Betelgeuse',
    author='Elyézer Rezende',
    author_email='erezende@redhat.com',
    version=VERSION,
    py_modules=['betelgeuse'],
    install_requires=['click', 'testimony'],
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2.7',
    ],
    description=('Betelgeuse reads standard Python test cases and offers '
                 'tools to interact with Polarion.'),
    entry_points='''
        [console_scripts]
        betelgeuse=betelgeuse:cli
    ''',
    license='GPLv3',
    long_description=LONG_DESCRIPTION,
    url='https://github.com/SatelliteQE/betelgeuse',
)
