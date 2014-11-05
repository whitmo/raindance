from .util import reify
from functools import partial
from futures import ProcessPoolExecutor
from path import path
from pprint import pformat
import json
import logging
import requests
import subprocess

logger = logging.getLogger(__name__)


class PackageArchive(object):
    """
    Represents fs representation of a package archive
    """
    log = logger

    def __init__(self, root_url, software=None, version=None, arch=None):
        self.root_url = root_url
        self.version = version
        self.arch = arch
        self.software = software

    @reify
    def http(self):
        return requests.Session()

    def grab_manifest(self):
        mani_url = path(self.root_url) / "index.json"
        res = self.http.get(mani_url)
        if not res.ok:
            raise RuntimeError('Request for %s failed: %s',  mani_url, res)
        manifest = res.json()
        return manifest

    def save_arch_manifest(self, software, version, verdir, arch):
        afname = '{}.json'.format(arch)
        archfile = verdir / afname
        if archfile.exists():
            return archfile, json.loads(archfile.text())

        archurl = path(self.root_url) / software / version / afname
        res = self.http.get(str(archurl))
        if not res.ok:
            raise RuntimeError('Request for %s failed: %s',  archurl, res)

        archfile.write_text(res.text)
        return archfile, res.json()

    def match_versions(self, releases):
        for version in releases:
            spec = version, arch = version
            if not any((self.version, self.arch)):
                yield spec
            elif self.version and self.arch:
                if self.version == version and self.arch == arch:
                    yield spec
            else:
                if self.version == version or self.arch == arch:
                    yield spec

    @staticmethod
    def release_template_paths(outdir, software, version):
        (reldir, pkgdir, verdir) = \
            (
                outdir / software,
                outdir / software / 'packages',
                outdir / software / version
            )
        return reldir, pkgdir, verdir

    @staticmethod
    def verify_file(path, sha1):
        return path.read_hexhash('sha1') == sha1, "sha mismatch: %s" % path

    @staticmethod
    def wget(url, outfile):
        retry = True
        while retry:
            logger.info('Downloading %s to %s' % (url, outfile))
            try:
                cmd = ['wget', '-t0', '-c', '-nv', str(url), '-O', outfile]
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                if e.returncode == 4:  # always retry network errors
                    logger.warn('Network error, retrying download: %s', url)
                    retry = True
                else:
                    raise
            else:
                retry = False
        return outfile

    def save_packages(self, software, pkgdir, packages):
        fpkg = partial(fetch_pkg, self.root_url, software, pkgdir)
        with ProcessPoolExecutor() as exe:
            out = exe.map(fpkg, packages)
            for result in out:
                yield result

    def build_mirror_section(self, targetdir, software, releases, jobs=None):
        """
        Build a local mirror of a section of a remote package archive.

        Returns a generator that (lazily) fetches each file into the mirror.
        """
        for version, arch in releases:
            dirs = self.release_template_paths(targetdir, software, version)
            [d.makedirs_p() for d in dirs]
            reldir, pkgdir, verdir, = dirs
            archfile, archdata = self.save_arch_manifest(software, version,
                                                         verdir, arch)
            yield archfile

            jobmd = verdir / 'jobs.tgz'
            if not jobmd.exists() or not self.verify_file(jobmd, archdata['jobs_sha1']):
                self.save_job_metadata(verdir, software, version)
            assert self.verify_file(jobmd, archdata['jobs_sha1'])
            yield jobmd

            if jobs is None:
                jobs = [job['name'] for job in archdata['jobs']]
            packages = [package for job in archdata['jobs']
                        for package in job['packages']
                        if job['name'] in jobs]

            for package in self.save_packages(software, pkgdir, packages):
                yield package

    def save_job_metadata(self, targetdir, software, version):
        url = path(self.root_url) / software / version / 'jobs.tgz'
        res = self.http.get(url)
        if not res.ok:
            raise RuntimeError('Request for %s failed: %s', url, res)
        targetdir.makedirs_p()
        newfile = targetdir / "jobs.tgz"
        newfile.write_bytes(res.content)
        return newfile

    def mirror_package_archive(self, targetdir, software):
        manifest = self.grab_manifest()
        all_releases = manifest['releases']

        if software is None:
            raise NotImplementedError("No support for entire archive download")

        releases = self.match_versions(all_releases[software])
        genpa = self.build_mirror_section(targetdir, software, releases)
        return [x for x in genpa]

    def tarextract(self, tarball, outdir, *args):
        outdir.makedirs_p(mode=0755)
        with outdir:
            subprocess.check_call(['tar', '-xzf', tarball] + list(args))

    def setup_job(self, mirror_root, target_path, software, version, arch, job_name):
        """
        Install a job from a local mirror to the target path.

        Returns a generator that processes each folder extracted from the mirror.
        """
        archfile = mirror_root / software / version / '{}.json'.format(arch)
        archdata = json.loads(archfile.text())
        jobsdata = {x['name']: x['packages'] for x in archdata['jobs']}
        packages = jobsdata.get(job_name, False)
        assert packages, "Job %s not in %s" % (job_name, jobsdata)

        jobs_file = mirror_root / software / version / 'jobs.tgz'
        jobs_target = target_path / 'jobs'
        self.tarextract(jobs_file, jobs_target, './{}'.format(job_name))
        yield path('jobs') / job_name

        for package in packages:
            package_file = mirror_root / software / 'packages' / package['filename']
            package_target = target_path / 'packages' / package['name']
            self.tarextract(package_file, package_target)
            yield path('packages') / package['name']

    @classmethod
    def mirror_cmd(cls, ctx, pargs):
        targetdir = pargs.mirror_dir
        root_url = pargs.index
        software, version = pargs.spec
        arch = pargs.arch

        pa = cls(root_url, version=version, arch=arch)

        targetdir.makedirs_p()
        files = pa.mirror_package_archive(targetdir, software)
        pa.log.debug(pformat(files))
        return 0


mirror_pa = PackageArchive.mirror_cmd


def fetch_pkg(root_url, software, pkgdir, pkg,
              verify=PackageArchive.verify_file, wget=PackageArchive.wget):
    outpath = pkgdir / pkg['filename']
    pkg_url = path(root_url) / software / 'packages' / pkg['filename']
    if not outpath.exists() or not verify(outpath, pkg['sha1']):
        wget(pkg_url, outpath)
    assert verify(outpath, pkg['sha1'])
    return outpath
