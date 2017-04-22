#!/usr/bin/env python
# coding=utf-8
"""A setuptools-based script for installing Betelgeuse."""
from setuptools import find_packages, setup

with open('README.rst') as handle:
    LONG_DESCRIPTION = handle.read()

with open('VERSION') as handle:
    VERSION = handle.read().strip()

setup(
    name='Betelgeuse',
    author='Elyézer Rezende, Og Maciel',
    author_email='erezende@redhat.com, omaciel@redhat.com',
    version=VERSION,
    packages=find_packages(include=['betelgeuse', 'betelgeuse.*']),
    install_requires=['click', 'docutils'],
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
    include_package_data=True,
    license='GPLv3',
    long_description=LONG_DESCRIPTION,
    package_data={'': ['LICENSE']},
    url='https://github.com/SatelliteQE/betelgeuse',
)
