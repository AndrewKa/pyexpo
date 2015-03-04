def func(a, b='2'):
    print a, b


# this will be overridden by function 'F'
class F(object):
    def f(self):
        print id(self)


def F():
    print id(F)


# this will be overridden by class 'F2'
def F2():
    print id(F2)


class F2(object):
    pass
