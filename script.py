import pkgutil
import sys


def get_module_filename(python_path):
    try:
        mloader = pkgutil.get_loader(python_path)
    except:
        mloader = None
    if mloader is None:
        print 'empty'
    else:
        print mloader.get_filename()


sys.path += sys.argv[1:]
