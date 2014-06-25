from . import util
from boto.exception import S3ResponseError
from path import path
import gevent
import gevent.monkey
import logging
import s3po
import subprocess
import tarfile
import yaml


gevent.monkey.patch_all()

logger = logging.getLogger(__name__)


class UploadJobArtefacts(object):
    manifest = 'compiled_packages.MF'
    def __init__(self, workdir, release, logger=logger):
        self.release = release
        self.manifest = workdir / self.manifest
        self.blobs = workdir / 'compiled_packages/blobs'
        self.outdir = workdir / 'artefacts'
        self.workdir = workdir
        self.log = logger

    @property
    def manifest_data(self):
        return util.load_yaml(self.manifest)

    def setup(self):
        if not self.outdir.exists():
            self.outdir.makedirs_p()

    def extract_packages(self, exported_packages, workdir):
        tgz = tarfile.open(exported_packages, 'r:gz')
        tgz.extractall(workdir)

    def dependency_data(self, packages, export_data):
        for package in packages:
            out = export_data.get(package, (None, None))
            if all(out):
                yield package, out
            else:
                yield (package, (False, False))

    def copy_packages(self, jobtmp, depdata):
        packages = jobtmp / 'packages'
        packages.mkdir_p()
        for pkg, (sha1, blobid) in depdata:
            if blobid is False:
                yield False, pkg
                break

            blob = self.blobs / blobid
            self.log.debug("%s %s", blob.basename(), blob.exists())

            self.verify_file(blob, sha1)

            dest = packages / '%s-%s.tgz' %(pkg, sha1)
            blob.copy(dest)
            yield True, pkg

    def populate_job_templates(self):
        export_data = util.packages_from_manifest(self.manifest_data)
        jobdata = ((job, job.packages) for job in self.release.joblist)

        for job, packages in jobdata:
            tmp = self.workdir / job.basename()
            job.copytree(tmp)
            depdata = self.dependency_data(packages, export_data)
            for status, pkg in self.copy_packages(tmp, depdata):
                if status is False:
                    self.log.error('ATT: No pkg %s for %s', pkg, job.basename())
            yield tmp

    def verify_file(self, path, sha1):
        assert path.read_hexhash('sha1') == sha1, "sha mismatch: %s" % path

    def tarzip_jobs(self, template_dirs):
        for dir in template_dirs:
            dest = self.outdir / dir.basename()
            with util.pushd(dir), tarfile.open(dest, 'w:gz') as tgz:
                tgz.add('.')
            yield dest

    def checkout_release(self, sha):
        with util.pushd(self.release):
            subprocess.check_call('git checkout %s' %sha, shell=True)

    @classmethod
    def command(cls, ctx, pargs):
        logger.info(pargs.workdir)
        release = ctx['release']

        uja = cls(pargs.workdir, release)
        uja.setup()

        if not uja.manifest.exists():
            uja.extract_packages(pargs.exported_packages, pargs.workdir)

        sha = uja.manifest_data['release_commit_hash']
        uja.checkout_release(sha)

        tds = uja.populate_job_templates()

        for tarball in uja.tarzip_jobs(tds):
            uja.log.info("Finished %s", tarball)
        print(tarball.parent)


create_artefacts = UploadJobArtefacts.command


class UploadExport(object):
    name_tmplt = "{release_name}-{release_version}-{release_commit_hash}-amd64.tar.gz"

    def __init__(self, filepath, bucket, s3cxn):
        self.bucket = bucket
        self.filepath = path(filepath).abspath()
        self.s3 = s3cxn

    def extract_manifest_data(self):
        tgz = tarfile.open(self.filepath, 'r:gz')
        fp = tgz.extractfile('compiled_packages.MF')
        data = yaml.load(fp)
        return data

    def upload(self, release_data):
        key = self.name_tmplt.format(**release_data)
        with open(self.filepath) as stream:
            self.s3.upload(self.bucket, key, stream, headers={'Content-Type':'application/x-tar'}, retries=3)

    @classmethod
    def command(cls, ctx, pargs):
        creds = pargs.access_key, pargs.secret_key

        assert all(creds), "Missing AWS Credentials: a: '%s', s:'%s'" % creds

        s3 = s3po.Connection(*creds)
        try:
            s3.conn.get_bucket(pargs.bucket)
        except S3ResponseError:
            s3.conn.create_bucket(pargs.bucket)

        uploader = cls(pargs.tarball, pargs.bucket, s3)
        data = uploader.extract_manifest_data()
        uploader.upload(data)
        return 0


upload_export = UploadExport.command
