import os


class abs_dir(object):
    def __init__(self, path):
        abspath = path
        if not os.path.isabs(path):
            abspath = os.path.abspath(path)
        if not os.path.isabs(abspath):
            raise ValueError("expected abs path, but got '%s'" % abspath)
        if os.path.isdir(abspath):
            self.parent = abspath
        else:
            self.parent = os.path.dirname(abspath)
    def __div__(self, relpath):
        return os.path.join(self.parent, relpath)

