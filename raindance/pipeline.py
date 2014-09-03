from . import util
from .package import PackageArchive
from path import path
import boto
import json
import logging
import requests
import tarfile

logger = logging.getLogger(__name__)


class UpdateReleaseManifest(object):

    def gen_rel_data(self, bucket):
        """
        abuses convention of arch manifests
        """
        archkeys = (key.name.split() for key in bucket.list() \
                if key.name != 'index.json' and key.name.endswith('.json'))

        for soft, version, _, archfile in archkeys:
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
        idxk = bucket.get_key('index.json')
        idxk.set_contents_from_string(outstring)
        return 0

    @util.reify
    def http(self):
        return requests.Session()

    @util.reify
    def s3(self):
        return boto.connect_s3()



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

    def do_prep(self):
        [d.mkdir() for d in self.dir_template]

        pkglist = self.verified_pkg_list

        jobdata = [(job, job.packages) for job in self.release.joblist]

        job_tgz_map = {x: y.basename() for x, y in \
                       self.create_job_tgzs(self.jobdir, jobdata)}

        pkg_map = {pkg: (sha1, dest.basename()) \
                   for pkg, sha1, dest, _ in pkglist()}

        [blob.copy(dest) for _, _, dest, blob in pkglist()]

        amd = self.arch_manifest_data(jobdata, pkg_map, job_tgz_map)
        arch_txt = json.dumps(dict(jobs=list(amd)), indent=2)
        self.archfile.write_text(arch_txt)

        self.release_sha1.write_text(self.commit_hash)

    @classmethod
    def command(cls, ctx, pargs):
        logger.info(pargs.workdir)
        release = ctx['release']
        assert release.exists()

        pe = cls(pargs.workdir, pargs.outdir, release)

        assert not pe.outdir.exists(), "%s exists. Please move "\
          "or change directory for output"

        pe.do_prep()
        return pe
