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
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description=(
        'Betelgeuse is a Python program that reads standard Python test cases '
        'and generates XML files that are suited to be imported by Polarion '
        'importers.'
    ),
    entry_points="""
        [console_scripts]
        betelgeuse=betelgeuse:cli
    """,
    include_package_data=True,
    license='GPLv3',
    long_description=LONG_DESCRIPTION,
    package_data={'': ['LICENSE']},
    url='https://github.com/SatelliteQE/betelgeuse',
)
