import os
import re
import sublime
import sublime_plugin
import subprocess


SETTINGS_FILE = 'Python Path to File.sublime-settings'
settings = sublime.load_settings(SETTINGS_FILE)

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
SYNTAX_FILENAME = os.path.join(LOCAL_DIR, 'Python Module Path.tmLanguage')
COLOR_SCHEME_FILENAME = os.path.join(LOCAL_DIR, 'Python Module Path.stTheme')

SCRIPT_PATH = os.path.join(LOCAL_DIR, 'module_finder.py')
module_path_pattern = re.compile(r'^\.*\w+(\.\w+)*$')


def debug(obj):
    with open(os.path.join(LOCAL_DIR, 'debug.txt'), 'ab') as f:
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
        if not module_path_pattern.match(input):
            sublime.status_message('Invalid python path: "%s"' % input)
            return

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
        python.stdin.write('get_module_filename("%s")\n' % python_path.replace(r'"', r'\"'))
        result = python.stdout.readline().lstrip('>').strip()
        python.kill()
        return result if result != 'empty' else None
