from paver.easy import task, needs, path, sh, cmdopts, options
from paver.setuputils import setup

import os
import sys

# add the current directory as the first listing on the python path
# so that we import the correct version.py
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import version


setup(name='ipython-helpers',
      version=version.getVersion(),
      author='Christian Fobel',
      author_email='christian@fobel.net',
      url='https://github.com/cfobel/ipython-helpers',
      license='LGPL-3.0',
      install_requires=['IPython>=2.0', 'path_helpers>=0.2'],
      packages=['ipython_helpers'])

@task
def nosetests():
    nose_options = '-v'
    sh('nosetests %s' % nose_options)

@task
@needs('generate_setup', 'minilib', 'nosetests',
       'setuptools.command.sdist')
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass


@task
@needs('generate_setup', 'minilib', 'nosetests',
       'setuptools.command.bdist_wheel')
def bdist_wheel():
    """Overrides bdist_wheel to make sure that our setup.py is generated."""
    pass

