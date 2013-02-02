from fnmatch import fnmatch
import imp
import os
import os.path as path
import re
import sublime
import sublime_plugin
import subprocess
import sys


SETTINGS_FILE = 'Python Open Module (New).sublime-settings'
settings = sublime.load_settings(SETTINGS_FILE)
prefs = sublime.load_settings('Preferences.sublime-settings')

LOCAL_DIR = path.dirname(path.abspath(__file__))
SYNTAX_FILENAME = path.join(LOCAL_DIR, 'Python Module Path.tmLanguage')
COLOR_SCHEME_FILENAME = path.join(LOCAL_DIR, 'Python Module Path.stTheme')

si = None
if hasattr(subprocess, 'STARTUPINFO'):
    si = subprocess.STARTUPINFO()
    si.dwFlags = subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE


def debug(obj):
    with open(path.join(LOCAL_DIR, 'debug.txt'), 'ab') as f:
        f.write('%(line)s\n%(obj)s\n%(line)s\n\n' %
            {'line': '=' * 40, 'obj': obj})


class PythonOpenModuleNewCommand(sublime_plugin.WindowCommand):

    def run(self):
        view = self.window.active_view()
        text = '' if view is None else view.substr(view.sel()[0])
        panel_view = self.window.show_input_panel('Python module path:', text, self.on_done, None, None)
        panel_view.sel().clear()
        panel_view.sel().add(panel_view.visible_region())
        panel_view.settings().set('syntax', SYNTAX_FILENAME)
        panel_view.settings().set('color_scheme', COLOR_SCHEME_FILENAME)

    def on_done(self, input):
        match = re.match(r'^\s*(?P<new_window>\+?)\s*(?P<dots>\.*)(?P<absolute_path>(?:\w+)?(?:\.\w+)*)\s*$', input)
        if not match:
            sublime.status_message('Invalid python module path: `%s`' % input)
            return

        open_new_window = match.group('new_window')
        dots = match.group('dots')
        absolute_path = match.group('absolute_path')
        input = '%s%s' % (dots, absolute_path)

        if dots:
            filename = self._get_relative_module_filename(dots, absolute_path)
        elif absolute_path:
            filename = self._get_absolute_module_filename(absolute_path)
        else:
            return

        if filename is None:
            sublime.status_message('Module `%s` not found' % input)
        else:
            sublime.status_message('Module `%s` found: %s' % (input, filename))

            if open_new_window:
                self._open_new_window(filename)
            elif self._is_inside_project(filename):
                self.window.open_file(filename)
                self.window.run_command('reveal_in_side_bar')
            else:
                self.window.open_file(filename, sublime.TRANSIENT)

    def _open_new_window(self, filename):
        subl_command = 'sublime_text' if sublime.platform() == 'windows' else 'subl'
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
            sublime.status_message('Unable to open `%s` in a new window.'
                'Make sure `%s` is in $PATH.' % (filename, subl_command))

    def _is_inside_project(self, filename):
        filename = path.realpath(filename)
        for folder in self.window.folders():
            folder = path.realpath(folder)
            if folder == filename:
                return True
            folder += os.sep
            if path.commonprefix([folder, filename]) == folder:
                return True
        return False

    def _get_project_folders(self):
        '''Return all the project directories, which contain a python package.
        '''
        exclude_folders = [path.join('*', folder) for folder in prefs.get('folder_exclude_patterns', [])]
        project_folders = set()

        def include(dir_path):
            return all(not fnmatch(dir_path, x) for x in exclude_folders)

        for root_folder in self.window.folders():
            for root, folders, files in os.walk(root_folder):
                # include only top-level packages
                if self._get_python_script(root, '__init__'):
                    project_folders.add(path.dirname(root))
                    folders[:] = []
                else:
                    folders[:] = filter(lambda x: include(path.join(root, x)), folders)
        return list(project_folders)

    def _get_sys_path(self):
        '''Return the sys path to be searched.
        We cannot simply use sys.path inside sublime script, because it is different.
        Also take into account user preferences, such as venv, path setting and
        current project.
        '''
        path_modifications = settings.get('path',
            {'prepend': [], 'append': [], 'replace': []})

        if path_modifications.get('replace'):
            result_path = path_modifications['replace']
        else:
            python_exec = settings.get('python_executable') or 'python'
            try:
                python = subprocess.Popen(
                    [python_exec, '-u', '-c', 'import sys; print sys.path'],
                    stdout=subprocess.PIPE,
                    startupinfo=si
                )
                result_path = eval(python.communicate()[0])
            except:
                result_path = sys.path
        return (path_modifications.get('prepend', []) +
                result_path +
                path_modifications.get('append', []) +
                self._get_project_folders())

    def _get_python_script(self, dir_path, script_name):
        '''Return the absolute path to the python script `script_name`
        (given without an extension) which should be contained somewhere inside
        `dir_path` directory.
        '''
        for ext in settings.get('python_extensions', ['.py']):
            filename = path.join(dir_path, script_name + ext)
            if path.exists(filename):
                return path.abspath(filename)

    def _get_absolute_module_filename(self, absolute_path, start_path=None):
        '''Return the absolute path to the python script from the given
        absolute module path.
        '''
        sys_path = self._get_sys_path() if start_path is None else start_path
        try:
            if absolute_path:
                for bit in absolute_path.split('.'):
                    sys_path = [imp.find_module(bit, sys_path)[1]]
            python_filename = sys_path[0]
            if path.isdir(python_filename):
                python_filename = self._get_python_script(python_filename, '__init__')
            return python_filename
        except:
            pass

    def _get_relative_module_filename(self, dots, absolute_path):
        '''Return the absolute path to the python script from the given
        relative module path. Relative path is relative to the working file.
        '''
        view = self.window.active_view()
        if view is None:
            return
        start_path = view.file_name()
        for d in dots:
            start_path = path.dirname(start_path)
        return self._get_absolute_module_filename(absolute_path, [start_path])
