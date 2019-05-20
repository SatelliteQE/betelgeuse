# coding=utf-8
"""Sphinx documentation generator configuration file.

The full set of configuration options is listed on the Sphinx website:
http://sphinx-doc.org/config.html
"""
from __future__ import unicode_literals

import os
import re
import sys


# Add the Betelgeuse root directory to the system path. This allows
# references such as :mod:`betelgeuse.whatever` to be processed
# correctly.
ROOT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    os.path.pardir
))
sys.path.insert(0, ROOT_DIR)

# We pass the raw version string to Version() to ensure it is compliant with
# PEP 440. An InvalidVersion exception is raised if the version is
# non-conformant, so the act of generating documentation serves as a unit test
# for the contents of the `VERSION` file.
#
# We use the raw version string when generating documentation for the sake of
# human friendliness: the meaning of '2016.02.18' is presumably more intuitive
# than the meaning of '2016.2.18'. The regex enforcing this format allows
# additional segments. This is done to allow multiple releases in a single day.
# For example, 2016.02.18.3 is the fourth release in a given day.
with open(os.path.join(ROOT_DIR, 'VERSION')) as handle:
    VERSION = handle.read().strip()
    assert re.match(r'\d+\.\d+\.\d+', VERSION) is not None

# Project information  ---------------------------------------------------

project = u'Betelgeuse'
copyright = u'2015, Satellite QE'
version = release = VERSION

# General configuration --------------------------------------------------

author = 'Satellite QE'
autodoc_default_flags = ['members']
exclude_patterns = ['_build']
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosectionlabel',
]
master_doc = 'index'
nitpicky = True
source_suffix = '.rst'

# Options for format-specific output -------------------------------------

htmlhelp_basename = 'Betelgeusedoc'
latex_documents = [(
    master_doc,
    project + '.tex',
    project + ' Documentation',
    author,
    'manual'
)]
man_pages = [(
    master_doc,
    project.lower(),
    project + ' Documentation',
    [author],
    1
)]
texinfo_documents = [(
    master_doc,
    project,
    project + ' Documentation',
    author,
    project,
    ('Betelgeuse reads standard Python test cases and generates XML files '
     'that are suited to be imported by Polarion importers.'),
    'Miscellaneous'
)]
