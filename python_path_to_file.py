import os.path as path
import re
import sublime
import sublime_plugin
import subprocess


SETTINGS_FILE = 'Python Path to File.sublime-settings'
settings = sublime.load_settings(SETTINGS_FILE)

LOCAL_DIR = path.dirname(path.abspath(__file__))
SYNTAX_FILENAME = path.join(LOCAL_DIR, 'Python Module Path.tmLanguage')
COLOR_SCHEME_FILENAME = path.join(LOCAL_DIR, 'Python Module Path.stTheme')

SCRIPT_PATH = path.join(LOCAL_DIR, 'module_finder.py')
module_path_pattern = re.compile(r'^\.*\w+(\.\w+)*$')


def debug(obj):
    with open(path.join(LOCAL_DIR, 'debug.txt'), 'ab') as f:
        f.write('%(line)s\n%(obj)s\n%(line)s\n\n' %
            {'line': '=' * 40, 'obj': obj})


class PythonPathToFileCommand(sublime_plugin.WindowCommand):

    def run(self):
        view = self.window.active_view()
        text = view.substr(view.sel()[0])
        view = self.window.show_input_panel('Python module path', text, self.on_done, None, None)
        view.settings().set('syntax', SYNTAX_FILENAME)
        view.settings().set('color_scheme', COLOR_SCHEME_FILENAME)

    def on_done(self, input):
        input = input.strip()
        if not input:
            return
        if not module_path_pattern.match(input):
            sublime.status_message('Invalid python path: "%s"' % input)
            return

        if input.startswith('.'):
            filename = self._get_relative_module_filename(input)
        else:
            filename = self._get_module_filename(input)

        if filename is None:
            sublime.status_message('Module "%s" not found' % input)
        else:
            sublime.status_message('Module "%s" found: %s' % (input, filename))
            self.window.open_file(filename, sublime.TRANSIENT)

    def _get_module_filename(self, python_path):
        si = None
        if hasattr(subprocess, 'STARTUPINFO'):
            si = subprocess.STARTUPINFO()
            si.dwFlags = subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
        python = subprocess.Popen(
            ['python', '-u', '-i', SCRIPT_PATH] + settings.get('path', []),
            shell=False,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=None,
            startupinfo=si
        )
        stdout, stderr = python.communicate('get_module_filename("%s")' % python_path)
        stdout = stdout.strip()
        return stdout if stdout != 'empty' else None

    def _get_python_script(self, dir_path, script_name):
        for ext in settings.get('python_extensions', []):
            filename = path.join(dir_path, script_name + ext)
            if path.exists(filename):
                return filename

    def _is_package(self, dir_path):
        return bool(self._get_python_script(dir_path, '__init__'))

    def _get_relative_module_filename(self, python_path):
        python_path = python_path.split('.')

        filename = self.window.active_view().file_name()
        for bit in python_path[:-1]:
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
        return self._get_python_script(filename, python_path[-1])
