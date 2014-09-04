from mock import Mock
from path import path
import json
import tempfile


class TestPrepExport(object):
    here = path(__file__).parent

    prepdir = here / 'prep_dummy'
    pkg_out_name = "dummy_package-6b02ba72f6d0285a65166048b2e4522d7c126f7f.tgz"
    howmany_jobs = 6

    def makeone(self, release=None):
        self.outdir = path(tempfile.mkdtemp(prefix='rd-test-')) / 'out'
        from raindance import pipeline as pl
        from raindance.release import Release
        self.release = Release(self.prepdir / 'release')
        return pl.PrepExport(self.prepdir, self.outdir, self.release)

    def makeone_cmd(self):
        from raindance.pipeline import PrepExport
        from raindance.release import Release
        pargs = Mock(name='pargs')
        pargs.exported_packages = self.prepdir
        pargs.outdir = path(tempfile.mkdtemp(prefix='rd-test-')) / 'out'
        ctx = dict(release=Release(self.prepdir / 'release'))
        pe = PrepExport.command(ctx, pargs)
        return pe

    def test_init(self):
        pe = self.makeone()
        assert pe
        assert not pe.outdir.exists()

    def test_command(self):
        assert self.makeone_cmd() == 0

    def test_command_metadata(self):
        pe = self.makeone()
        pe.do_prep()

        af = json.loads(pe.archfile.text())
        assert len(af['jobs']) == self.howmany_jobs
        record = next(job for job in af['jobs'] \
                      if job['name'] == 'dummy_with_package')

        plist = record.get('packages', [])

        assert len(plist) == 1
        assert set(plist[0].keys()) == set(('name', 'sha1', 'filename'))
        assert plist[0]['sha1'] == "6b02ba72f6d0285a65166048b2e4522d7c126f7f"
        assert plist[0]['filename'] == self.pkg_out_name
        assert plist[0]['name'] == "dummy_package"

    def test_proper_pkg_naming_and_placement(self):
        pe = self.makeone()
        pe.do_prep()

        pkgs = pe.pkgdir.files()
        assert len(pkgs) == 1
        assert pkgs[0].basename() == self.pkg_out_name

    def test_naming_and_placement(self):
        pe = self.makeone()
        pe.do_prep()

        assert pe.jobsfile.exists()
