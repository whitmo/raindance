import yaml


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
