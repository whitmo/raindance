from mock import Mock
from mock import patch
import requests
import unittest

class TestPackageArchive(unittest.TestCase):
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
        with patch('raindance.package.PackageArchive.grab_manifest') as gm:
            from raindance.package import PackageArchive
            with self.assertRaises(NotImplementedError):
                PackageArchive.mirror_package_archive('.', 'http://url', None)

    def test_mirror_package_archive(self):
        with patch('raindance.package.PackageArchive.grab_manifest') as gm:
            from raindance.package import PackageArchive
            gm.return_value = dict(releases=dict(dummy=(('1234', 'amd64'),)))
            import pdb;pdb.set_trace()
            PackageArchive.mirror_package_archive('.', 'http://url', 'dummy')
