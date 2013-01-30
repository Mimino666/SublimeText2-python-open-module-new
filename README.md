Python Open Module (New)
========================

Plugin to Sublime Text 2.
Opens the Python module file based on the Python import path.


More advanced and bugfree version of [PythonOpenModule](https://github.com/SublimeText/PythonOpenModule).

Typical usecase
===============

You are reading a Python script and trying to understand why it works the way it works.


At the top of the script you see `from some.very.mysterious.module import muhahaha`.
Are you curious what `muhahaha()` is doing? Simple enough!


Highlight `some.very.mysterious.module`, press <kbd>Alt+Shift+o</kbd>, <kbd>Enter</kbd> and enjoy.

Features
========

* works with virtual environments
* easy modification of sys.path contents through settings
* automatically discoveres and includes Python packages in your currently opened project
* handles relative paths
* user-friendly input panel with syntax highlighting (i.e. if you type bullshit, it turns red)
* you can choose whether to view the modules in the current or a new window

Install
=======

The easiest way to install this is with [Package Control](http://wbond.net/sublime_packages/package_control).

Usage
=====

Press <kbd>Alt+Shift+o</kbd> to open the input panel. Type the Python import path of the module you want to view.


_Note:_ this plugin STRICTLY simulates the Python's import mechanism.
What it means is that you can view only such files that Python would be able to import from the current working file.
The only exception are your project packages, which are automatically included in sys.path for you.


Suppose the following directory tree of your Python project:

    MyProject/
      x.py
      A/
        __init__.py
        y.py            <- current working file
        B/
          __init__.py
          z.py

Examples:

    Type into input panel   ->  What file is opened (sys.path prefix to file ommited):
    ----------------------------------------------------------------------------------
    os                      ->  os.py
    django.db               ->  django.db.__init__.py

    Prefix import paths with `+` to open them in a new window:
    ----------------------------------------------------------
    +os                     ->  Opens os.py in a new window.
    +django                 ->  Opens whole django project in a new window (because `django` is a package).

    Inside your project (MyProject/ is automatically included to sys.path):
    -----------------------------------------------------------------------
    x                       ->  x.py
    A.y                     ->  A/y.py
    A.B.z                   ->  A/B/z.py

    Relative paths are resolved based on the current working file:
    --------------------------------------------------------------
    .B.z                    ->  A/B/z.py
    .B                      ->  A/B/__init__.py
    .                       ->  A/__init__.py

If you try to input a path that Python would not be able to import from the current working file, nothing will be
opened and you will receive an information in the status bar (at the bottom of ST2 window).

Virtual environment
-------------------

If you are using virtual environment, you need to set the setting `python_executable`
(Preferences > Package Settings > PythonOpenModule(New) > Settings - User)
to the path to the Python executable inside your venv directory.

Modifying sys.path
------------------

Use the setting `path` to modify the contents of sys.path, used for module search. See the default settings for reference

FAQ
===

### Plugin doesn't work for `sys` or `datetime` modules. Is it a bug?

No it is not a bug. Some modules simply doesn't have .py files available, thus cannot be opened.
For example `sys` module is on your system probably as `sysmodule.c` file.
For other modules, maybe only .pyc files are available.
There is nothing that can be done about this. Sorry.
