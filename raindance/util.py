import yaml
import gevent
import logging

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
        self._cache = None

    def __get__(self, path, type=None):
        if self.loader is None:
            return path / self.name
        if self._cache is None:
            self._cache = self.loader(path / self.name)
        return self._cache


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
