#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

from setuptools import setup

import os
import sys

# add the current directory as the first listing on the python path
# so that we import the correct version.py
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import version


setup(name='jupyter-helpers',
      version=version.getVersion(),
      author='Christian Fobel',
      author_email='christian@fobel.net',
      url='https://github.com/sci-bots/jupyter-helpers',
      license='BSD',
      install_requires=['notebook', 'jupyter', 'path_helpers>=0.2', 'psutil'],
      packages=['jupyter_helpers'])
