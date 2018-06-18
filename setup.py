#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

from setuptools import setup

import versioneer


setup(name='jupyter-helpers',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      author='Christian Fobel',
      author_email='christian@fobel.net',
      url='https://github.com/sci-bots/jupyter-helpers',
      license='BSD',
      install_requires=['notebook', 'jupyter', 'path_helpers>=0.2', 'psutil'],
      packages=['jupyter_helpers'])
