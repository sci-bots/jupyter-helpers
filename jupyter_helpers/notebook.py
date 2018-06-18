# coding: utf-8
from Queue import Queue, Empty
from collections import OrderedDict
from subprocess import Popen, PIPE
from threading import Thread
import os
import psutil
import re
import sys
import time
import webbrowser

from path_helpers import path


def kill_process_tree(pid, including_parent=True):
    '''
    Cross-platform function to kill a parent process and all child processes.

    Based on from `subprocess: deleting child processes in Windows <https://stackoverflow.com/a/4229404/345236>`_

    Parameters
    ----------
    pid : int
        Process ID of parent process.
    including_parent : bool, optional
        If ``True``, also kill parent process.


    .. versionadded:: 0.11
    '''
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        child.kill()
    gone, still_alive = psutil.wait_procs(children, timeout=5)
    if including_parent:
        parent.kill()
        parent.wait(5)


class Session(object):
    '''
    This class provides an API for launching a Jupyter notebook process
    (non-blocking).
    '''
    def __init__(self, daemon=False, create_dir=False, timeout_s=20, **kwargs):
        '''
        Arguments
        ---------
        daemon : bool, optional
            Kill notebook process when `Session` object is deleted.
        create_dir : bool, optional
            Create the notebook directory, if necessary.
        timeout_s : int or float, optional
            Time to wait for notebook process to initialize (in seconds).

        See also
        --------
        SessionManager.get_session
        '''
        self.daemon = daemon
        if create_dir and 'notebook_dir' in kwargs:
            path(kwargs['notebook_dir']).makedirs_p()
        self.timeout_s = timeout_s
        self.kwargs = kwargs
        self.process = None
        self.thread = None
        self.stderr_lines = []
        self.port = None
        self.token = None
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
        Launch Jupyter notebook server in background process.

        Arguments and keyword arguments are passed on to `Popen` call.

        By default, notebook server is launched using current working directory
        as the notebook directory.


        .. versionchanged:: 0.11
            Check ``PYTHONEXEPATH`` environment variable for explicit path to
            Python executable.  Useful, e.g., when running from a Py2Exe
            application where an alternate ``.exe`` file should be used to
            launch the notebook server.

            Modify the server URL regular expression to match the following
            server output format:

                [I 13:03:10.907 NotebookApp] The Jupyter Notebook is running at:
                [I 13:03:10.907 NotebookApp] http://localhost:8888/?token=<...>

            Note that the text "The ... Notebook is running at:" is no longer
            output on the same line as the server URL.
        '''
        if 'stderr' in kwargs:
            raise ValueError('`stderr` must not be specified, since it must be'
                             ' monitored to determine which port the notebook '
                             'server is running on.')

        args_ = (os.environ.get('PYTHONEXEPATH', sys.executable),
                 '-m', 'jupyter', 'notebook') + self.args
        args_ = args_ + tuple(args)

        # Launch notebook as a subprocess and read stderr in a new thread.
        # See: https://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python

        ON_POSIX = 'posix' in sys.builtin_module_names

        def enqueue_output(out, queue):
            for line in iter(out.readline, b''):
                queue.put(line)
            out.close()

        self.process = Popen(args_, stderr=PIPE, bufsize=1, close_fds=ON_POSIX, **kwargs)
        q = Queue()
        self.thread = Thread(target=enqueue_output, args=(self.process.stderr, q))
        self.thread.daemon = self.daemon # thread dies with the program
        self.thread.start()
        self._notebook_dir = os.getcwd()

        # Determine which port the notebook is running on.
        cre_address = re.compile(r'(?P<address>https?://.*?:'
                                 r'(?P<port>\d+)/)\?token=(?P<token>[a-z0-9]+)\r?$')
        cre_notebook_dir = re.compile(r'Serving notebooks from local '
                                      r'directory:\s+(?P<notebook_dir>[^\r]*)\r?$')
        match = None
        self.stderr_lines = []
        start_time = time.time()

        while self.is_alive() and match is None:
            # read line without blocking
            try:
                stderr_line = q.get_nowait()
            except Empty:
                pass
            else: # got line
                self.stderr_lines.append(stderr_line)
                match = cre_address.search(stderr_line)
                dir_match = cre_notebook_dir.search(stderr_line)
                if dir_match:
                    self._notebook_dir = dir_match.group('notebook_dir')
            if time.time() - start_time > self.timeout_s:
                # Timeout has been exceeded.
                raise RuntimeError('Timed out waiting for notebook process to '
                                   'launch.')

        if match:
            # Notebook was started successfully.
            self.address = match.group('address')
            self.port = int(match.group('port'))
            self.token = match.group('token')
        else:
            self.stop()
            raise IOError(''.join(self.stderr_lines))

    @property
    def notebook_dir(self):
        if self._notebook_dir is None:
            raise ValueError('Notebook directory not set.  Is the notebook '
                             'server running?')
        return path(self._notebook_dir)

    def resource_filename(self, filename):
        '''
        Return full path to resource within notebook directory based on the
        specified relative path.

        Inspired by the [`resource_filename`][1] function of the
        [`pkg_resources`][2] package.

        Parameters
        ----------
        filename : str
            Path relative to notebook directory.

        Returns
        -------
        path_helpers.path
            Full path to resource within notebook directory based on the
            specified relative path.

        [1]: https://pythonhosted.org/setuptools/pkg_resources.html#resource-extraction
        [2]: https://pythonhosted.org/setuptools/pkg_resources.html
        '''
        return self.notebook_dir.joinpath(filename)

    def is_alive(self):
        '''
        Returns
        -------
        bool
            ``True`` if notebook process is running.
        '''
        if self.thread:
            return self.thread.is_alive()
        else:
            return False


    def open(self, filename=None):
        '''
        Open a browser tab with the notebook path specified relative to the
        notebook directory.

        If no filename is specified, open the root of the notebook server.

        Parameters
        ----------
        filename : str
            Notebook file path relative to notebook directory.
        '''
        if filename is None:
            address = self.address + 'tree'
        else:
            notebook_path = self.resource_filename(filename)
            if not notebook_path.isfile():
                raise IOError('Notebook path not found: %s' % notebook_path)
            else:
                address = '%snotebooks/%s' % (self.address, filename)
        webbrowser.open_new_tab(address + '?token=' + self.token)

    def stop(self):
        '''
        Kill the notebook server process, if running.


        .. versionchanged:: 0.11
            Use :func:`kill_process_tree` to ensure notebook server process and
            _all child processes_ are stopped.
        '''
        if self.daemon and self.process is not None:
            kill_process_tree(self.process.pid)
            self.process = None
            self.thread = None

    def __del__(self):
        try:
            self.stop()
        except (Exception, ), exception:
            print exception


class SessionManager(object):
    def __init__(self, daemon=True):
        '''
        Parameters
        ----------
        daemon : bool, optional
            If ``True``, kill notebook processes when ``Session`` object is
            deleted.
        '''
        self.sessions = OrderedDict()
        self.daemon = daemon

    def open(self, filepath=None, **kwargs):
        '''
        Parameters
        ----------
        filepath : str, optional
            Notebook file to open.

            If no file path is specified, launch a notebook process in the
            current working directory.
        '''
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
        Launch a copy of the specified `.ipynb` (template) file in a Jupyter
        notebook session for the specified notebook directory.

        If a Jupyter notebook session has already been launched for the
        notebook directory, reuse it.

        If no notebook directory is specified, use the current working directory.

        Parameters
        ----------
        template_path : str
            Path to template `.ipynb` file.
        notebook_dir : str, optional
            Directory to start Jupyter notebook session in.
        overwrite : bool, optional
            If ``True``, overwrite existing file in ``notebook_dir``, if
            necessary.
        output_name : str, optional
            Name of notebook file (defaults to the name as the template file).
        create_dir : bool, optional
            If ``True``, create notebook directory, if necessary.
        no_browser : bool, optional
            If ``True``, do not launch new browser tab.
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
            # Open Jupyter notebook in new browser tab.
            session.open(notebook_path.name)

    def get_session(self, notebook_dir=None, no_browser=True, **kwargs):
        '''
        Return handle to Jupyter notebook session for specified notebook directory.

        If a Jupyter notebook session has already been launched for the
        notebook directory, reuse it.  Otherwise, launch a new Jupyter notebook
        session.

        By default, notebook session is launched using current working
        directory as the notebook directory.

        Parameters
        ----------
        notebook_dir : str, optional
            Directory to start Jupyter notebook session in.
        no_browser : bool, optional
            Do not launch new browser tab (default: ``True``).
        **kwargs : dict
            Additional arguments to pass along to ``Session`` constructor.

        Returns
        -------
        Session
            Handle to Jupyter notebook session for specified notebook directory.

        See Also
        --------
        :class:`Session`
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
            # start new Jupyter notebook process.

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
