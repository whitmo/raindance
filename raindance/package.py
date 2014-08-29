from .util import reify
from path import path
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
        #@@ add support for version range
        self.root_url = root_url
        self.software = software
        self.version = version
        self.arch = arch

    @reify
    def http(self):
        return requests.Session()

    def grab_manifest(self):
        mani_url = path(self.root_url) / "index.json"
        res = self.http.get(mani_url)
        if not res.ok():
            raise RuntimeError('Request for %s failed: %s',  mani_url, res)
        manifest = res.json()
        return manifest

    def save_arch_manifest(self, software, version, archdir, arch):
        afname = '{}.json'.format(arch)
        archurl = path(self.root_url) / software / version / 'arch' / afname
        archfile = archdir / afname
        res = self.http.get(str(archurl))
        if not res.ok():
            raise RuntimeError('Request for %s failed: %s',  archurl, res)
        archfile.write_text(res.text)
        return archfile, res.json()

    def match_versions(self, releases):
        for version in releases:
            version, arch = version
            if not any((self.version, self.arch)):
                yield version

            if self.version == version or self.arch == arch:
                yield version

    @staticmethod
    def release_template_paths(outdir, software, version):
        (reldir, pkgdir, verdir, jobdir, archdir) = \
            (
                outdir / software,
                outdir / software / 'packages',
                outdir / software / version,
                outdir / software / version / 'jobs',
                outdir / software / version / 'arch'
            )
        return reldir, pkgdir, verdir, jobdir, archdir

    def save_job_metadata(self, jobdir, filename, software, version):
        url = path(self.root_url) / software / version / 'jobs' / filename
        res = self.http.get(url)
        if not res.ok():
            raise RuntimeError('Request for %s failed: %s',  archurl, res)
        newfile = jobdir / filename
        newfile.write_bytes(res.content)
        return newfile

    @staticmethod
    def verify_file(path, sha1):
        assert path.read_hexhash('sha1') == sha1, "sha mismatch: %s" % path

    @staticmethod
    def wget(self, url, outfile):
        retry = True
        while retry:
            self.log.info('Downloading %s to %s' % (url, outfile))
            try:
                cmd = ['wget', '-t0', '-c', '-nv', url, '-O', outfile]
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                if e.returncode == 4:  # always retry network errors
                    self.log.warn('Network error, retrying download: %s', url)
                    retry = True
                else:
                    raise
            else:
                retry = False

    def save_packages(self, pkgdir, packages):
        for pkg in packages:
            outpath = pkgdir / pkg
            pkg_url = path(self.root_url) / self.release
            self.verfiy_file(outpath, pkg['sha1'])

    def build_mirror_section(self, targetdir, software, releases):
        for version, arch in releases:
            dirs = self.release_template_paths(targetdir, software, version)
            [d.makedirs_p() for d in dirs]
            reldir, pkgdir, verdir, jobdir, archdir = dirs
            archfile, archdata = self.save_arch_manifest(software, version,
                                                         archdir, arch)
            yield archfile

            # could be concurrent
            for job in archdata['jobs']:
                yield self.save_job_metadata(jobdir, job['metadata'])
                for package in self.save_packages(job['packages']):
                    yield package

    @classmethod
    def mirror_package_archive(cls, targetdir, root_url, software='cf',
                               version=None, arch='amd64'):

        pa = cls(root_url, software, version, arch)
        manifest = pa.grab_manifest()
        all_releases = manifest['releases']

        if software is None:
            raise NotImplementedError("No support for entire archive download")

        releases = pa.match_versions(all_releases[software])
        genpa = pa.build_mirror_section(targetdir, software, releases)
        return [x for x in genpa]
