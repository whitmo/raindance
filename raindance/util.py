from contextlib import contextmanager
from path import path
import gevent
import logging
import yaml

logger = logging.getLogger(__name__)


class Waiter(list):
    def __init__(self):
        self.greenlets = []

    def spawn(self, func, *args, **kw):
        g = gevent.spawn(func, *args, **kw)
        self.greenlets.append(g)

    @property
    def results(self):
        for greenlet in self.greenlets:
            status = greenlet.successful()
            yield status, greenlet.value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if any(args):
            raise
        gevent.wait(self.greenlets)


class filepath(object):
    def __init__(self, name, loader=None):
        self.name = name
        self.loader = loader

    def __get__(self, path, type=None):
        if self.loader is None:
            return path / self.name
        if not getattr(path, '_fpcache', None):
            path._fpcache = self.loader(path / self.name)
        return path._fpcache


class submap_value(object):

    def __init__(self, attr, key):
        self.attr = attr
        self.key = key

    def __get__(self, obj, type=None):
        mapping = getattr(obj, self.attr)
        return mapping[self.key]


def load_yaml(path):
    with open(path) as stream:
        return yaml.load(stream, yaml.SafeLoader)


@contextmanager
def pushd(newdir):
    newdir = path(newdir)
    curdir = path('.').abspath()
    try:
        newdir.chdir()
        yield newdir
    finally:
        curdir.chdir()


def packages_from_manifest(data):
    data = dict((x['package_name'],
                 (x['compiled_package_sha1'],
                  x['blobstore_id'])) for x in data['compiled_packages'])
    return data


class reify(object):
    """
    from pyramid, licensing applies: https://github.com/Pylons/pyramid/blob/master/LICENSE.txt

    Use as a class method decorator.  It operates almost exactly like the
    Python ``@property`` decorator, but it puts the result of the method it
    decorates into the instance dict after the first call, effectively
    replacing the function it decorates with an instance variable.  It is, in
    Python parlance, a non-data descriptor.  An example:

    .. code-block:: python

       class Foo(object):
           @reify
           def jammy(self):
               print('jammy called')
               return 1

    And usage of Foo:

    >>> f = Foo()
    >>> v = f.jammy
    'jammy called'
    >>> print(v)
    1
    >>> f.jammy
    1
    >>> # jammy func not called the second time; it replaced itself with 1
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped
        try:
            self.__doc__ = wrapped.__doc__
        except: # pragma: no cover
            pass

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self
        val = self.wrapped(inst)
        setattr(inst, self.wrapped.__name__, val)
        return val
