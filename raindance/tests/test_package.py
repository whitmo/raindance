from mock import patch
from mock import Mock
from path import path
import contextlib
import requests
import unittest
import tempfile


class TestPackageArchive(unittest.TestCase):
    here = path(__file__).parent
    fakepkg = here / 'prep_dummy/compiled_packages/'\
      'blobs/e8be9b00-ca2b-42b3-50bf-7c8f1d749908'

    archdata = here / "amd64.json"
    dummy_pkg = here / "dummy_with_package.tgz"

    pam = "raindance.package.PackageArchive.{}".format
    jobtgz = here / 'jobs.tgz'

    @property
    def outdir(self):
        return path(tempfile.mkdtemp(prefix='rd-test-')) / 'out'

    def makeone(self, url='http://someurl', software="dummy", version='100'):
        from raindance.package import PackageArchive
        return PackageArchive(url, software, version)

    def test_init(self):
        pa = self.makeone()
        assert pa
        assert isinstance(pa.http, requests.Session)

    def test_grab_manifest_bad_response(self):
        pa = self.makeone()
        with patch(self.pam('http'),
                   spec=requests.Session) as httpm:
            httpm.get().ok = False
            with self.assertRaises(RuntimeError):
                pa.grab_manifest()

    def test_grab_manifest(self):
        pa = self.makeone()
        with patch(self.pam('http'),
                   spec=requests.Session) as http:
            marker = http.get().json()
            assert marker is pa.grab_manifest()

    def test_mirror_package_archive_no_software(self):
        with patch(self.pam('grab_manifest')):
            from raindance.package import PackageArchive
            with self.assertRaises(NotImplementedError):
                PackageArchive('http://url').mirror_package_archive('.', None)

    def test_setup_job(self):
        out = self.outdir
        pa = self.makeone()
        gen = pa.setup_job(self.here / 'data', out, 'dummy', '100', 'amd64', 'dummy_with_package')

        self.assertEqual(list(gen), [
            path('jobs/dummy_with_package'),
            path('packages/dummy_package'),
        ])
        assert (out / 'jobs/dummy_with_package/spec').exists()
        assert not (out / 'jobs/dummy_with_properties/spec').exists()
        assert (out / 'packages/dummy_package/some_dummy_package').exists()

    def patch_set(self, *methods):
        return contextlib.nested(*[patch(self.pam(x)) for x in methods])

    def test_mirror_package_archive(self):
        outdir = self.outdir

        with self.patch_set('grab_manifest', 'http', 'wget') as (gm, hm, wm):
            from raindance.package import PackageArchive

            def wget_se(url, outfile):
                assert url == path(u'http://url/dummy/packages/dp-1234.tgz')
                assert outfile.endswith('out/dummy/packages/dp-1234.tgz')
                self.fakepkg.copy(outfile)
                return outfile

            wm.side_effect = wget_se
            gm.return_value = dict(releases=dict(dummy=(('1234', 'amd64'),)))
            hm.get().text = "ARCH DESC"
            hm.get().content = b"IM A FILE"
            pkg = dict(name='dp',
                       sha1='6b02ba72f6d0285a65166048b2e4522d7c126f7f',
                       filename='dp-1234.tgz')
            dj = dict(jobs=[dict(name='dummyjob',
                                 packages=(pkg,))],
                      jobs_sha1='993fe02fd8f6f6fb36c9bb6a3a66e6a801297acc')
            hm.get().json.return_value = dj

            report = PackageArchive('http://url')\
                .mirror_package_archive(outdir,  'dummy')
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

    def test_mirror_section_partial(self):
        with self.patch_set('release_template_paths',
                            'save_arch_manifest',
                            'save_job_metadata',
                            'verify_file',
                            'save_packages') as (rtp, sam, sjm, vf, sp):
            _, pkg, vdr = rtp.return_value = [Mock() for i in range(3)]
            vdr.__div__ = Mock()
            sam.return_value = ['archfile', {'jobs': [
                {'name': 'job1', 'packages': ['p1', 'p2']},
                {'name': 'job2', 'packages': ['p3', 'p4']},
                {'name': 'job3', 'packages': ['p5', 'p6']},
            ], 'jobs_sha1': 'sha'}]
            pa = self.makeone()
            list(pa.build_mirror_section(
                'targetdir', 'software', [('version', 'arch')], 'job2'))
            sp.assert_called_once_with('software', pkg, ['p3', 'p4'])
