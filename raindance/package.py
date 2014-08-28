from path import path
import requests




class PackageArchive(object):
    """
    Represents fs representation of a package archive
    """

    def __init__(self, root_url, software=None, version=None, arch=None):
        #@@ add support for version range
        self.root_url = root_url
        self.software = software
        self.version = version
        self.arch = arch
        self.http = requests.Session()

    def grab_manifest(self):
        res = self.http.get(root_url)
        if not res.ok():
            raise RuntimeError('Request for %s failed: %s',  root_url, res)
        manifest = res.json()
        return manifest

    def save_arch_manifest(self, software, version, archdir, arch):
        archurl = path(self.root_url) / software / version / 'arch' / afname
        afname = '{}.json'.format(arch)
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

    def save_packages(self, pkgdir, packages):
        for pkg in packages:
            outpath = _
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
