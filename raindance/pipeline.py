from . import util
from .package import PackageArchive
from boto.exception import S3ResponseError
from path import path
import gevent
import gevent.monkey
import logging
import s3po
import subprocess
import tarfile
import yaml
import json


gevent.monkey.patch_all()

logger = logging.getLogger(__name__)


class PrepExport(object):
    manifest = 'compiled_packages.MF'

    def __init__(self, packages, outdir, release, arch='amd64', logger=logger):
        self.release = release
        self.packages = packages
        self.manifest = packages / self.manifest
        self.blobs = packages / 'compiled_packages/blobs'
        self.outdir = outdir
        self.arch = arch
        self.log = logger

        self.release_number = self.manifest_data['release_version']
        self.commit_hash = self.manifest_data['release_commit_hash']
        self.release_name = self.manifest_data['release_name']

        subtemplate = (
            self.reldir,
            self.pkgdir,
            self.verdir,
            self.jobdir,
            self.archdir
            ) = PackageArchive.release_template_paths(self.outdir,
                                                      self.release_name,
                                                      self.release_number)

        self.dir_template = (self.outdir,) + subtemplate

        self.archfile = self.archdir / ("%s.json" % self.arch)
        self.release_sha1 = self.reldir / 'release-sha1.txt'
        self.logger = logger

    @util.reify
    def export_data(self):
        data = self.manifest_data
        return [(x['package_name'],
                 (x['compiled_package_sha1'],
                  x['blobstore_id'])) for x in data['compiled_packages']]

    @util.reify
    def manifest_data(self):
        return util.load_yaml(self.manifest)



    def dependency_data(self, packages, export_data):
        for package in packages:
            out = export_data.get(package, (None, None))
            if all(out):
                yield package, out
            else:
                yield (package, (False, False))

    def create_job_tgzs(self, jobdir, jobdata):
        for job, packages in jobdata:
            tmp = jobdir / job.basename()
            job.copytree(tmp)
            dest = jobdir / "{}.tgz".format(job.basename())
            with util.pushd(tmp), tarfile.open(dest, 'w:gz') as tgz:
                tgz.add('.')
            tmp.rmtree()
            yield job, dest

    verify_file = staticmethod(PackageArchive.verify_file)

    def verified_pkg_list(self):
        for pkg, (sha1, bsid) in self.export_data:
            blob = self.blobs / bsid
            self.verify_file(blob, sha1)
            new_name = '%s-%s.tgz' % (pkg, sha1)
            dest = self.pkgdir / new_name
            yield pkg, sha1, dest, blob

    def pkr(self, name, (sha1, version)):
        return dict(name=name, sha1=sha1, filename=version)

    def arch_manifest_data(self, jobdata, pkg_map, tgz_map):
        for job, pkgs in jobdata:
            packages = []
            error = False
            for pkg in pkgs:
                pkg_data = pkg_map.get(pkg, None)
                if pkg_data is None:
                    self.logger.warn("Bad package: %s", pkg)
                    error = True
                    continue
                packages.append(self.pkr(pkg, pkg_data))
            out = dict(name=job.basename(),
                       metadata=tgz_map[job],
                       packages=packages)
            if error is True:
                out['error'] = True
            yield out

    @classmethod
    def command(cls, ctx, pargs):
        logger.info(pargs.workdir)
        release = ctx['release']
        assert release.exists()

        pe = cls(pargs.workdir, pargs.outdir, release)

        assert not pe.outdir.exists(), "%s exists. Please move "\
          "or change directory for output"

        [d.mkdir() for d in pe.dir_template]

        pkglist = pe.verified_pkg_list

        jobdata = [(job, job.packages) for job in pe.release.joblist]

        job_tgz_map = {x: y.basename() for x, y in \
                       pe.create_job_tgzs(pe.jobdir, jobdata)}

        pkg_map = {pkg: (sha1, dest.basename()) \
                   for pkg, sha1, dest, _ in pkglist()}

        [blob.copy(dest) for _, _, dest, blob in pkglist()]

        amd = pe.arch_manifest_data(jobdata, pkg_map, job_tgz_map)
        arch_txt = json.dumps(dict(jobs=list(amd)), indent=2)
        pe.archfile.write_text(arch_txt)

        pe.release_sha1.write_text(pe.commit_hash)
        return pe





class UploadJobArtefacts(object):
    # deprecated
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
        assert release.exists()

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
