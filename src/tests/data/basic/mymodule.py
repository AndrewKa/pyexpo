def one_func(arg, kwarg1=None):
    "Do something"
    if kwarg1 is None:
        print "Hello, %s" % arg
    else:
        print "%s, %s" % (arg, kwarg1)
