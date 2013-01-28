import sublime
import sublime_plugin
import subprocess


SETTINGS_FILE = 'Python Path to File.sublime-settings'
settings = sublime.load_settings(SETTINGS_FILE)


class PythonPathToFileCommand(sublime_plugin.WindowCommand):

    def __init__(self, *args, **kwargs):
        super(PythonPathToFileCommand, self).__init__(*args, **kwargs)

    def _get_module_filename(self, python_path):
        si = None
        if hasattr(subprocess, 'STARTUPINFO'):
            si = subprocess.STARTUPINFO()
            si.dwFlags = subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
        python = subprocess.Popen(
            ['python', '-u', '-i', 'script.py'] + settings.get('path', []),
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

    def run(self):
        view = self.window.active_view()
        text = view.substr(view.sel()[0])
        self.window.show_input_panel('Python module name', text, self.on_done, self.on_change, self.on_cancel)

    def on_done(self, input):
        filename = self._get_module_filename(input)
        if filename is None:
            sublime.status_message('Module %s not found' % input)
        else:
            sublime.status_message('Module %s found on %s' % (input, filename))
            self.window.open_file(filename, sublime.TRANSIENT)

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass
