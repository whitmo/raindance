from . import util
from .package import PackageArchive
from path import path
import boto
import json
import logging
import requests
import tarfile
import tempfile

logger = logging.getLogger(__name__)


class UpdateReleaseManifest(object):

    def gen_rel_data(self, bucket):
        """
        abuses convention of arch manifests
        """
        archkeys = [key.name.split('/') for key in bucket.list() \
                if key.name != 'index.json' and key.name.endswith('.json')]

        for soft, version, archfile in archkeys:
            yield soft, [version, archfile.replace('.json', '')]

    @classmethod
    def command(cls, ctx, pargs):
        urm = cls()
        bucket = urm.s3.get_bucket(pargs.bucket)

        releases = dict()

        for soft, rel in urm.gen_rel_data(bucket):
            rels = releases.setdefault(soft, [])
            rels.append(rel)

        outstring = json.dumps(dict(releases=releases), indent=2)
        idxk = bucket.new_key('index.json')
        idxk.content_type = 'application/json'
        idxk.set_contents_from_string(outstring)
        idxk.set_canned_acl('public-read')
        return 0

    @util.reify
    def http(self):
        return requests.Session()

    @util.reify
    def s3(self):
        return boto.connect_s3()


update_release_manifest = UpdateReleaseManifest.command


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
            self.verdir
            ) = PackageArchive.release_template_paths(self.outdir,
                                                      self.release_name,
                                                      self.release_number)

        self.dir_template = (self.outdir,) + subtemplate

        self.jobsfile = self.verdir / 'jobs.tgz'
        self.archfile = self.verdir / ("%s.json" % self.arch)
        self.release_sha1 = self.verdir / 'sha1.txt'
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

    @staticmethod
    def create_jobs_tgz(jobssrc, release, target):
        tmpdir = path(tempfile.mkdtemp(prefix='jobs-%s' % release))
        with tarfile.open(target, 'w:gz') as tgz:
            with tmpdir:
                for fd in jobssrc.listdir():
                    if fd.islink():
                        fd = fd.readlinkabs()
                    path(fd).copytree(tmpdir / fd.basename())
                tgz.add('.')
        return target

    @classmethod
    def pack_jobs(cls, ctx, pargs):
        release = ctx['release']
        assert release.exists()

        jobfile = cls.create_jobs_tgz(release.jobs,
                                      pargs.release,
                                      pargs.outfile)
        print(jobfile.abspath())
        return 0

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

    def arch_manifest_data(self, jobdata, pkg_map):
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
                       packages=packages)
            if error is True:
                out['error'] = True
            yield out

    def do_prep(self):
        [d.mkdir() for d in self.dir_template]

        jobdata = [(job, job.packages) for job in self.release.joblist]

        jobsfile = self.create_jobs_tgz(self.release.jobs,
                                        self.release,
                                        self.jobsfile)

        jobs_sha1 = jobsfile.read_hexhash('sha1')

        pkglist = list(self.verified_pkg_list())

        for _, _, dest, blob in pkglist:
            blob.copy(dest)

        pkg_map = {pkg: (sha1, dest.basename()) \
                   for pkg, sha1, dest, _ in pkglist}

        amd = self.arch_manifest_data(jobdata, pkg_map)
        arch_data = dict(jobs=list(amd),
                         jobs_sha1=jobs_sha1,
                         commit=self.commit_hash)

        arch_txt = json.dumps(arch_data, indent=2)

        self.archfile.write_text(arch_txt)
        return self

    @classmethod
    def command(cls, ctx, pargs):
        logger.info(pargs.exported_packages)
        release = ctx['release']
        assert release.exists()

        pe = cls(pargs.exported_packages, pargs.outdir, release)

        assert not pe.outdir.exists(), "%s exists. Please move "\
          "or change directory for output"

        pe.do_prep()
        return 0


prep_export = PrepExport.command
pack_jobs = PrepExport.pack_jobs
