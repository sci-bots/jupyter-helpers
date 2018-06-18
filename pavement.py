from paver.easy import task, needs, path, sh, cmdopts, options
from paver.setuputils import setup

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

