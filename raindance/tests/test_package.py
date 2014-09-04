from mock import Mock
from mock import patch
from path import path
import requests
import unittest
import tempfile


class TestPackageArchive(unittest.TestCase):
    here = path(__file__).parent
    fakepkg = here / 'prep_dummy/compiled_packages/'\
      'blobs/e8be9b00-ca2b-42b3-50bf-7c8f1d749908'

    def makeone(self, url='http://someurl', software="dummy", version='100'):
        from raindance.package import PackageArchive
        return PackageArchive(url, software, version)

    def test_init(self):
        pa = self.makeone()
        assert pa
        assert isinstance(pa.http, requests.Session)

    def test_grab_manifest_bad_response(self):
        pa = self.makeone()
        with patch('raindance.package.PackageArchive.http',
                   spec=requests.Session) as httpm:
            httpm.get().ok.return_value = False
            with self.assertRaises(RuntimeError):
                pa.grab_manifest()

    def test_grab_manifest(self):
        pa = self.makeone()
        with patch('raindance.package.PackageArchive.http',
                   spec=requests.Session) as http:
            marker = http.get().json()
            assert marker is pa.grab_manifest()

    def test_mirror_package_archive_no_software(self):
        with patch('raindance.package.PackageArchive.grab_manifest'):
            from raindance.package import PackageArchive
            with self.assertRaises(NotImplementedError):
                PackageArchive.mirror_package_archive('.', 'http://url', None)

    def test_mirror_package_archive(self):
        outdir = path(tempfile.mkdtemp(prefix='rd-test-')) / 'out'
        with patch('raindance.package.PackageArchive.grab_manifest') as gm,\
           patch('raindance.package.PackageArchive.http') as hm,\
           patch('raindance.package.PackageArchive.wget') as wm:
            from raindance.package import PackageArchive

            def wget_se(url, outfile):
                assert url == path(u'http://url/packages/dp-1234.tgz')
                assert outfile.endswith('out/dummy/packages/dp-1234.tgz')
                self.fakepkg.copy(outfile)
                return outfile

            wm.side_effect = wget_se
            gm.return_value = dict(releases=dict(dummy=(('1234', 'amd64'),)))
            archd = hm.get().text = "ARCH DESC"
            jobd = hm.get().content = b"IM A FILE"
            dj = dict(jobs=[dict(name='dummyjob',
                                 packages=(dict(name='dp',
                                                sha1='6b02ba72f6d0285a65166048b2e4522d7c126f7f',
                                                filename='dp-1234.tgz'),)
                        )])
            hm.get().json.return_value = dj

            report = PackageArchive.mirror_package_archive(outdir, 'http://url', 'dummy')
            res1 = sorted(outdir.walk())
            assert set(report) <= set(res1)
            result = [x.replace(outdir, '.') for x in res1]

            # structure
            # {software} / {version} / {version artifact}
            # {software} / packages  / {package version}
            assert result == [u'./dummy',
                              u'./dummy/1234',
                              u'./dummy/1234/amd64.json',
                              u'./dummy/1234/jobs.tgz',
                              u'./dummy/packages',
                              u'./dummy/packages/dp-1234.tgz']
