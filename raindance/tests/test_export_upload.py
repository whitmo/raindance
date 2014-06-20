from itertools import count
from mock import Mock
from mock import patch
from mock import call
from path import path
from raindance.util import pushd
import tarfile


class TestUploadExport(object):
    here = path(__file__).parent
    def makeone(self, fp=here / 'dummy/dummy-compiled-packages.tgz'):
        from raindance.pipeline import UploadExport
        return UploadExport(fp, 'bucket', Mock(name='s3po'))

    def test_extract_manifest_data(self):
        ue = self.makeone()
        data = ue.extract_manifest_data()
        assert 'release_commit_hash' in data

    def test_upload_to_s3(self):
        ue = self.makeone()
        ue.s3 = Mock(name='s3')
        data = ue.extract_manifest_data()
        ue.upload(data)
        assert ue.s3.upload.called
        assert ue.s3.upload.call_args[0][1] == 'dummy-0+dev.3-9364d68b-amd64.tar.gz'


class TestUploadJobArtefacts(object):
    here = path(__file__).parent
    counter = count()
    sandbox = here / __name__
    manifest_template = here / 'index.yml'
    dummy = here /  'dummy'
    dummy_cpc = dummy / 'dummy-compiled-packages.tgz'
    dummy_release = dummy / 'release'

    def makeone(self, release=None):
        from raindance.pipeline import UploadJobArtefacts
        from raindance.release import Release
        self.release = release or Mock(name='release', spec=Release)
        return UploadJobArtefacts(self.sandbox, self.release)

    def setup(self):
        self.sandbox.rmtree_p()
        self.sandbox.mkdir()
        with tarfile.open(self.dummy_cpc, 'r:gz') as tgz, pushd(self.sandbox):
            tgz.extractall()

    def teardown(self):
        self.sandbox.rmtree_p()
        
    def test_instantiation(self):
        assert self.makeone()

    def test_setup(self):
        uja = self.makeone()
        uja.setup()
        assert (self.sandbox / 'artefacts').exists()

    def test_populate_template_pkg_placement(self):
        from raindance.release import Release
        uja = self.makeone(release=Release(self.dummy_release))
        uja.setup()
        uja.extract_packages(self.dummy_cpc, uja.workdir)
        uja.log = Mock(name='logger')
        out = next(x for x in uja.populate_job_templates() if x.endswith('dummy_with_package'))
        assert set([str(x.basename()) for x in out.files()]) == set(('monit', 'spec'))
        assert set([str(x.basename()) for x in out.dirs()]) == set(('templates', 'packages'))
        pkg = out / 'packages/dummy_package-6b02ba72f6d0285a65166048b2e4522d7c126f7f.tgz'
        assert pkg.exists()

    def test_populate_template_bad_package(self):
        from raindance.release import Release
        uja = self.makeone(release=Release(self.dummy_release))
        uja.setup()
        uja.extract_packages(self.dummy_cpc, uja.workdir)
        uja.log = Mock(name='logger')
        [x for x in uja.populate_job_templates()]
        assert uja.log.error.called
        assert 'bad_package' in uja.log.error.call_args[0]

    def test_checkout_release(self):
        from raindance.release import Release
        with patch('subprocess.check_call') as sp:
            uja = self.makeone(release=Release(self.dummy_release))
            uja.setup()
            sha = uja.manifest_data['release_commit_hash']
            uja.checkout_release(sha)
            assert sp.called
            assert sp.call_args == call('git checkout 9364d68b', shell=True)

        
    
