from mock import Mock
from mock import patch
from path import path
from raindance.util import load_yaml


class TestShrinkWrap(object):
    here = path(__file__).parent
    index = here / 'index.yml'
    index_data = load_yaml(index)

    @property
    def faux_deps(self):
        cpc3 = self.index_data['compiled_packages'][:3]
        for dep in cpc3:
            yield dep['package_name'], (dep['compiled_package_sha1'],
                                        dep['blobstore_id'])

    def makeone(self, url='http://index', rel='172'):
        from raindance.shrinkwrap import ShrinkWrap
        self.httpm = Mock(name='http')
        self.cachem = path('./test-cache')
        return ShrinkWrap(url, rel, self.httpm, self.cachem)

    def test_get_deps(self):
        sw = self.makeone()
        with patch('raindance.shrinkwrap.ShrinkWrap.download') as dl:
            dl.return_value = ('dummy', self.here / 'dummy')
            out = [x for x in sw.get_deps(self.faux_deps,
                                          self.here / 'deptest')]
        assert len(out) == 3
        assert out[0][0] == 'dummy'
        assert dl.called
        assert dl.call_args_list[0][0][3] == 'debian_nfs_server'

    def test_get_data(self):
        with patch('raindance.shrinkwrap.ShrinkWrap.save_or_reload') as sor:
            sw = self.makeone()
            sor.return_value = self.index
            data = sw.get_data('url')
        assert 'golang' in data.keys()
        assert len(data['golang']) == 2
        sha, blob = data['golang']
        assert sha, blob == ('71fb349bd573bbe8367b11ae7cce390a40c73dd7',
                             'f5a3585c-4308-47eb-6a51-d229e8f84a4a')
