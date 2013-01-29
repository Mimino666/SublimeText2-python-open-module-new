import imp
import os.path as path
import re
import sublime
import sublime_plugin
import subprocess
import sys


SETTINGS_FILE = 'Python Open Module New.sublime-settings'
settings = sublime.load_settings(SETTINGS_FILE)

LOCAL_DIR = path.dirname(path.abspath(__file__))
SYNTAX_FILENAME = path.join(LOCAL_DIR, 'Python Module Path.tmLanguage')
COLOR_SCHEME_FILENAME = path.join(LOCAL_DIR, 'Python Module Path.stTheme')

module_path_pattern = re.compile(r'^\s*\.*\w+(\.\w+)*\s*$')


def debug(obj):
    with open(path.join(LOCAL_DIR, 'debug.txt'), 'ab') as f:
        f.write('%(line)s\n%(obj)s\n%(line)s\n\n' %
            {'line': '=' * 40, 'obj': obj})


class PythonOpenModuleNewCommand(sublime_plugin.WindowCommand):

    def run(self):
        view = self.window.active_view()
        text = view.substr(view.sel()[0])
        panel_view = self.window.show_input_panel('Python module path', text, self.on_done, None, None)
        panel_view.sel().add(panel_view.visible_region())
        panel_view.settings().set('syntax', SYNTAX_FILENAME)
        panel_view.settings().set('color_scheme', COLOR_SCHEME_FILENAME)

    def on_done(self, input):
        input = input.strip()
        if not input:
            return
        if not module_path_pattern.match(input):
            sublime.status_message('Invalid python module path: "%s"' % input)
            return

        if input.startswith('.'):
            filename = self._get_relative_module_filename(input)
        else:
            filename = self._get_absolute_module_filename(input)

        if filename is None:
            sublime.status_message('Module "%s" not found' % input)
        else:
            sublime.status_message('Module "%s" found: %s' % (input, filename))
            self.window.open_file(filename, sublime.TRANSIENT)

    def _get_sys_path(self):
        '''Return the sys path to be searched.
        We cannot simply use sys.path inside sublime script, because it is different.
        Also take into account user preferences, such as venv, path setting and
        current project.
        '''
        try:
            si = None
            if hasattr(subprocess, 'STARTUPINFO'):
                si = subprocess.STARTUPINFO()
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
            python = subprocess.Popen(
                ['python', '-u', '-c', 'import sys; print sys.path'],
                shell=False,
                stdout=subprocess.PIPE,
                startupinfo=si
            )
            result_path = eval(python.communicate()[0])
        except:
            result_path = sys.path
        result_path += settings.get('path', [])
        return result_path

    def _get_python_script(self, dir_path, script_name):
        '''Return the absolute path to the python script "script_name"
        (given without an extension) which should be contained somewhere inside
        "dir_path" directory.
        '''
        for ext in settings.get('python_extensions', []):
            filename = path.join(dir_path, script_name + ext)
            if path.exists(filename):
                return path.abspath(filename)

    def _is_package(self, dir_path):
        '''True, if the "dir_path" points to a Python package directory.
        '''
        return path.isdir(dir_path) and bool(self._get_python_script(dir_path, '__init__'))

    def _get_absolute_module_filename(self, absolute_path):
        '''Return the absolute path to the python script from the given
        absolute module path.
        '''
        sys_path = self._get_sys_path()
        try:
            for bit in absolute_path.split('.'):
                sys_path = [imp.find_module(bit, sys_path)[1]]
            python_filename = sys_path[0]
            if path.isdir(python_filename):
                python_filename = self._get_python_script(python_filename, '__init__')
            return python_filename
        except:
            pass

    def _get_relative_module_filename(self, relative_path):
        '''Return the absolute path to the python script from the given
        relative module path. Relative path is relative to the working file.
        '''
        relative_path = relative_path.split('.')

        filename = self.window.active_view().file_name()
        for bit in relative_path[:-1]:
            if not bit:
                filename = path.dirname(filename)
            else:
                filename = path.join(filename, bit)
            if not path.exists(filename):
                return
            if not path.isdir(filename):
                return
            if not self._is_package(filename):
                return
        return self._get_python_script(filename, relative_path[-1])
