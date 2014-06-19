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
