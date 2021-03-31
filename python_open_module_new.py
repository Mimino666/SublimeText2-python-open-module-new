from fnmatch import fnmatch
from os import path
import imp
import os
import re
import subprocess
import sys
import threading
import time

import sublime
import sublime_plugin


SETTINGS_FILE = 'Python Open Module (New).sublime-settings'

SYNTAX_FILENAME = path.join('Packages', 'Python Open Module (New)', 'Python Module Path.tmLanguage')
COLOR_SCHEME_FILENAME = path.join('Packages', 'Python Open Module (New)', 'Python Module Path.stTheme')


si = None
if hasattr(subprocess, 'STARTUPINFO'):
    si = subprocess.STARTUPINFO()
    si.dwFlags = subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE


def debug(*args):
    LOCAL_DIR = path.dirname(path.abspath(__file__))
    with open(path.join(LOCAL_DIR, 'debug.txt'), 'a') as f:
        f.write('%(line)s\n%(obj)s\n%(line)s\n\n' %
                {'line': '=' * 40, 'obj': ' '.join(map(str, args))})


def get_settings():
    return sublime.load_settings(SETTINGS_FILE)


def get_preferences():
    return sublime.load_settings('Preferences.sublime-settings')


class ProjectPackagesManager(object):
    '''
    `ProjectPackagesManager` discovers and maintains the list of top-level
    Python packages in the current project.
    '''

    def __init__(self):
        self.packages = []
        self.running = False
        self.last_run = 0

    def refresh(self, window):
        cur_time = time.time()
        if not self.running and cur_time - self.last_run >= 60:
            self.running = True
            self.last_run = cur_time
            threading.Thread(target=self._discover_project_packages, kwargs={
                'root_folders': window.folders(),
                'folder_exclude_patterns': get_preferences().get('folder_exclude_patterns', []),
                'python_extensions': get_settings().get('python_extensions', ['.py']),
            }).start()

    def _discover_project_packages(self, root_folders, folder_exclude_patterns, python_extensions):
        exclude_folders = [path.join('*', one) for one in folder_exclude_patterns]
        init_filename_pattern = re.compile('__init__(%s)' % '|'.join(python_extensions).replace('.', r'\.'))
        project_packages = set()

        def is_ok(dirpath):
            return all(not fnmatch(dirpath, one) for one in exclude_folders)

        def is_package(filenames):
            return any(init_filename_pattern.match(filename) for filename in filenames)

        for root_folder in root_folders:
            for dirpath, dirnames, filenames in os.walk(root_folder):
                if is_package(filenames):
                    project_packages.add(path.dirname(dirpath))
                    dirnames[:] = []
                else:
                    dirnames[:] = filter(lambda dirname: is_ok(path.join(dirpath, dirname)),
                                         dirnames)

        self.packages = list(project_packages)
        self.running = False


class PythonOpenModuleNewCommand(sublime_plugin.WindowCommand):
    def __init__(self, *args, **kwargs):
        super(PythonOpenModuleNewCommand, self).__init__(*args, **kwargs)
        self.project_packages = ProjectPackagesManager()

    def run(self):
        self.project_packages.refresh(self.window)

        view = self.window.active_view()
        text = '' if view is None else view.substr(view.sel()[0])
        panel_view = self.window.show_input_panel(
            'Python module path:', text, self.on_done, None, None)
        panel_view.sel().clear()
        panel_view.sel().add(panel_view.visible_region())
        panel_view.settings().set('syntax', SYNTAX_FILENAME)
        panel_view.settings().set('color_scheme', COLOR_SCHEME_FILENAME)

    def on_done(self, text):
        match = re.match(
            r'^\s*(?P<new_window>\+?)\s*(?P<dots>\.*)'
            r'(?P<absolute_path>(?:\w+)?(?:\.\w+)*)\s*$',
            text)

        if not match:
            sublime.status_message('Invalid python module path: `%s`' % text)
            return

        open_new_window = match.group('new_window')
        dots = match.group('dots')
        absolute_path = match.group('absolute_path')
        text = '%s%s' % (dots, absolute_path)

        if dots:
            filename = self._get_relative_module_filename(dots, absolute_path)
        elif absolute_path:
            filename = self._get_absolute_module_filename(absolute_path)
        else:
            return

        if filename is None:
            sublime.status_message('Module `%s` not found' % text)
        else:
            sublime.status_message('Module `%s` found: %s' % (text, filename))

            if open_new_window:
                self._open_new_window(filename)
            elif self._is_inside_project(filename):
                self.window.open_file(filename)
                self.window.run_command('reveal_in_side_bar')
            else:
                self.window.open_file(filename, sublime.TRANSIENT)

    def _open_new_window(self, filename):
        if sublime.platform() == 'windows':
            subl_command = 'sublime_text'
        else:
            subl_command = 'subl'

        try:
            # for packages, open the whole directory
            if path.splitext(path.basename(filename))[0] == '__init__':
                dirname = path.dirname(filename)
            # for standalone python modules, open only the file
            else:
                dirname = ''
            subprocess.Popen(
                [subl_command, '-n', dirname, filename],
                startupinfo=si)
        except OSError:
            sublime.status_message(
                'Unable to open `%s` in a new window.'
                'Make sure `%s` is in $PATH.' % (filename, subl_command))

    def _is_inside_project(self, filename):
        filename = path.normcase(path.realpath(filename))
        for folder in self.window.folders():
            folder = path.normcase(path.realpath(folder))
            if folder == filename:
                return True

            folder += os.sep
            if path.commonprefix([folder, filename]) == folder:
                return True

        return False

    def _get_python_script(self, dirpath, script_name):
        '''
        Return the absolute path to the python script `script_name`
        (given without an extension) which should be contained somewhere inside
        `dirpath` directory.
        '''

        for ext in get_settings().get('python_extensions', ['.py']):
            filename = path.join(dirpath, script_name + ext)
            if path.exists(filename):
                return path.abspath(filename)

    def _get_absolute_module_filename(self, absolute_path, start_path=None):
        '''
        Return the absolute filepath to the python script from the given
        absolute module path.
        '''

        if start_path is None:
            sys_path, imported_modules = self._get_sys_path()
        else:
            sys_path, imported_modules = start_path, {}

        module_path_parts = absolute_path.split('.') if absolute_path else []
        # first try to look in `imported_modules`
        for num_parts in range(len(module_path_parts), 0, -1):
            prefix = '.'.join(module_path_parts[0:num_parts])
            if prefix in imported_modules:
                sys_path = [imported_modules[prefix]]
                del module_path_parts[0:num_parts]
                break

        try:
            for bit in module_path_parts:
                sys_path = [imp.find_module(bit, sys_path)[1]]
            python_filename = sys_path[0]
            if path.isdir(python_filename):
                return (self._get_python_script(python_filename, '__init__') or
                        python_filename)
            return python_filename
        except:
            pass

    def _get_relative_module_filename(self, dots, absolute_path):
        '''
        Return the absolute path to the python script from the given
        relative module path. Relative path is relative to the working file.
        '''

        view = self.window.active_view()
        if view is None:
            return

        start_path = view.file_name()
        # move up in directory structure for each dot
        for _ in dots:
            start_path = path.dirname(start_path)

        return self._get_absolute_module_filename(absolute_path, [start_path])

    def _get_sys_path(self):
        '''
        Return the sys path to be searched with user preferences (e.g. venv,
        path setting) and the current project taken into account.

        We cannot simply use sys.path inside the sublime script, because it is
        modified by ST. We need to ask external Python script for this.

        Update: as a second return value, return the dictionary of already
        imported modules (received from sys.modules). This solves problems
        with some .pth scripts
        (e.g. `zc` module from http://pypi.python.org/pypi/zc.queue)
        '''

        settings = get_settings()
        path_modifications = settings.get(
            'path',
            {'prepend': [], 'append': [], 'replace': []})

        imported_modules = {}
        if path_modifications.get('replace'):
            result_path = path_modifications['replace']
        else:
            python_exec = settings.get('python_executable') or 'python'
            try:
                python_script = (
                    'import sys;'
                    'print(sys.path);'
                    'print(dict((k, m.__path__[0]) for (k, m) in sys.modules.items() if hasattr(m, "__path__") and isinstance(m.__path__, list)));')
                python = subprocess.Popen(
                    [python_exec, '-u', '-c', python_script],
                    stdout=subprocess.PIPE,
                    startupinfo=si)
                result_path, imported_modules = map(eval, python.communicate()[0].decode('utf-8').split('\n')[:2])
            except:
                result_path = sys.path

        return (
            (
                path_modifications.get('prepend', []) +
                result_path +
                path_modifications.get('append', []) +
                self.project_packages.packages
            ),
            imported_modules)
