# coding: utf-8
from collections import OrderedDict
import webbrowser
from subprocess import Popen, PIPE
import sys
import os
import re

from path_helpers import path


class Session(object):
    '''
    This class provides an API for launching an IPython notebook process
    (non-blocking).
    '''
    def __init__(self, daemon=False, create_dir=False, **kwargs):
        '''
        Arguments
        ---------

         - `daemon`: Kill notebook process when `Session` object is deleted.
         - `create_dir`: Create the notebook directory, if necessary.
        '''
        self.daemon = daemon
        if create_dir and 'notebook_dir' in kwargs:
            path(kwargs['notebook_dir']).makedirs_p()
        self.kwargs = kwargs
        self.process = None
        self.stderr_lines = []
        self.port = None
        self.address = None
        self._notebook_dir = None

    @property
    def args(self):
        args = ()
        for k, v in self.kwargs.iteritems():
            cli_k = k.replace('_', '-')
            if v is None:
                args += ('--%s' % cli_k, )
            else:
                args += ('--%s=%s' % (cli_k, v), )
        return args

    def start(self, *args, **kwargs):
        '''
        Launch IPython notebook server in background process.

        Arguments and keyword arguments are passed on to `Popen` call.

        By default, notebook server is launched using current working directory
        as the notebook directory.
        '''
        if 'stderr' in kwargs:
            raise ValueError('`stderr` must not be specified, since it must be'
                             ' monitored to determine which port the notebook '
                             'server is running on.')
        args_ = ('%s' % sys.executable, '-m', 'IPython', 'notebook') + self.args
        args_ = args_ + tuple(args)
        self.process = Popen(args_, stderr=PIPE, **kwargs)
        self._notebook_dir = os.getcwd()

        # Determine which port the notebook is running on.
        cre_address = re.compile(r'The \w+ Notebook is running at: '
                                 r'(?P<address>https?://.*?:'
                                 r'(?P<port>\d+)[^\r]*/)\r?$')
        cre_notebook_dir = re.compile(r'Serving notebooks from local '
                                      r'directory:\s+(?P<notebook_dir>[^\r]*)\r?$')
        match = None
        self.stderr_lines = []

        while not self.process.poll() and match is None:
            stderr_line = self.process.stderr.readline()
            self.stderr_lines.append(stderr_line)
            match = cre_address.search(stderr_line)
            dir_match = cre_notebook_dir.search(stderr_line)
            if dir_match:
                self._notebook_dir = dir_match.group('notebook_dir')

        if match:
            # Notebook was started successfully.
            self.address = match.group('address')
            self.port = int(match.group('port'))
        else:
            raise IOError(''.join(self.stderr_lines))

    @property
    def notebook_dir(self):
        if self._notebook_dir is None:
            raise ValueError('Notebook directory not.  Is the notebook server '
                             'running?')
        return path(self._notebook_dir)

    def resource_filename(self, filename):
        '''
        Return full path to resource within notebook directory based on the
        specified relative path.

        Inspired by the [`resource_filename`][1] function of the
        [`pkg_resources`][2] package.


        [1]: https://pythonhosted.org/setuptools/pkg_resources.html#resource-extraction
        [2]: https://pythonhosted.org/setuptools/pkg_resources.html
        '''
        return self.notebook_dir.joinpath(filename)

    def is_alive(self):
        '''
        Return `True` if notebook process is running.
        '''
        return (self.process is not None) and (self.process.poll() is None)

    def open(self, filename=None):
        '''
        Open a browser tab with the notebook path specified relative to the
        notebook directory.

        If no filename is specified, open the root of the notebook server.
        '''
        if filename is None:
            address = self.address + 'tree'
        else:
            notebook_path = self.resource_filename(filename)
            if not notebook_path.isfile():
                raise IOError('Notebook path not found: %s' % notebook_path)
            else:
                address = '%snotebooks/%s' % (self.address, filename)
        webbrowser.open_new_tab(address)

    def stop(self):
        '''
        Kill the notebook server process, if running.
        '''
        if self.daemon and self.process is not None:
            self.process.kill()

    def __del__(self):
        try:
            self.stop()
        except (Exception, ), exception:
            print exception


class SessionManager(object):
    def __init__(self, daemon=True):
        '''
        Arguments
        ---------

         - `daemon`: Kill notebook processes when `Session` object is deleted.
        '''
        self.sessions = OrderedDict()
        self.daemon = daemon

    def open(self, filepath=None, **kwargs):
        if filepath is None:
            notebook_dir = path(os.getcwd())
            filename = None
        else:
            filepath = path(filepath)
            if not filepath.isfile():
                raise IOError('Notebook file not found: %s' % filepath)
            notebook_dir = path(filepath).abspath().parent
            filename = filepath.name
        daemon = kwargs.pop('daemon', self.daemon)
        session = self.get_session(notebook_dir, daemon=daemon, **kwargs)
        session.open(filename)

    def launch_from_template(self, template_path, notebook_dir=None,
                             overwrite=False, output_name=None,
                             create_dir=False, no_browser=False, **kwargs):
        '''
        Launch a copy of the specified `.ipynb` (template) file in an IPython
        notebook session for the specified notebook directory.

        If an IPython notebook session has already been launched for the
        notebook directory, reuse it.

        If no notebook directory is specified, use the current working directory.

        Arguments
        ---------

         - `template_path`: Path to template `.ipynb` file.
         - `notebook_dir`: Directory to start IPython notebook session in.
         - `overwrite`: Overwrite existing file in `notebook_dir`, if necessary.
         - `create_dir`: Create notebook directory, if necessary.
         - `no_browser`: Do not launch new browser tab.
        '''
        template_path = template_path.abspath()
        if output_name is None:
            output_name = template_path.name

        if notebook_dir is None:
            notebook_dir = path(os.getcwd())
        else:
            notebook_dir = path(notebook_dir).abspath()

        if template_path.parent.realpath() == notebook_dir.realpath():
            raise IOError('Notebook directory must not be the parent directory of '
                          'the template file.')
        else:
            # The parent of the template file is not the notebook directory.
            output_path = notebook_dir.joinpath(output_name)
            if output_path.isfile() and not overwrite:
                # A file with the same name already exists in the root.
                raise IOError('Notebook already exists with same name.')
            # Create notebook directory if it doesn't exist.
            if create_dir:
                notebook_dir.mkdirs_p()

            template_path.copy(output_path)
            notebook_path = output_path

        session = self.get_session(notebook_dir=notebook_dir, **kwargs)

        if not no_browser:
            # Open IPython notebook in new browser tab.
            session.open(notebook_path.name)

    def get_session(self, notebook_dir=None, no_browser=True, **kwargs):
        '''
        Return handle to IPython session for specified notebook directory.

        If an IPython notebook session has already been launched for the
        notebook directory, reuse it.  Otherwise, launch a new IPython notebook
        session.

        By default, notebook session is launched using current working
        directory as the notebook directory.

        Arguments
        ---------

         - `notebook_dir`: Directory to start IPython notebook session in.
         - `no_browser`: Do not launch new browser tab.
        '''
        if notebook_dir in self.sessions and self.sessions[notebook_dir].is_alive():
            # Notebook process is already running for notebook directory,
            session = self.sessions[notebook_dir]
            if 'daemon' in kwargs:
                # Override `daemon` setting of existing session.
                session.daemon = kwargs['daemon']
            if not no_browser:
                session.open()
        else:
            # Notebook process is not running for notebook directory, so
            # start new IPython notebook process.

            # Use default `daemon` setting for manager if no specified.
            daemon = kwargs.pop('daemon', self.daemon)
            if no_browser:
                kwargs['no_browser'] = None
            if notebook_dir is not None:
                kwargs['notebook_dir'] = notebook_dir
            session = Session(daemon=daemon, **kwargs)
            session.start()
            self.sessions[str(session.notebook_dir)] = session
        return session

    def stop(self):
        for session in (self.sessions.values()):
            session.stop()

    def __del__(self):
        self.stop()
