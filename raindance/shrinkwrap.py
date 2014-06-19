from .util import load_yaml
from .util import Waiter
from clint.textui import progress
from functools import partial
import gevent.monkey
import grequests
import json
import logging
import util

gevent.monkey.patch_all()
jdump = partial(json.dumps, indent=2)
logger = logging.getLogger(__name__)


class ShrinkWrap(object):
    manifest = 'index.yml'

    def __init__(self, index_url, release, http=None, cache=None):
        self.index_url = index_url
        self.release = release
        self.cache = cache
        self.http = http or grequests.Session()

    def resolve_deps(self, job):
        manifest_url = '/'.join((self.index_url, self.manifest))
        data = self.get_data(manifest_url)

        dep_data = [(pkg, data[pkg]) for pkg in job.packages]
        results = [x for x in self.get_deps(dep_data,
                                            self.cache)]
        return results

    def save_or_reload(self, url, dest):
        http = self.http
        if dest.exists():
            resp = http.head(url)
            if not resp.ok:
                logger.error("Issue with connecting to %s: %s", url, resp)
                return dest

            if '"%s"' % dest.read_hexhash('md5') == resp.headers['etag']:
                logger.debug("loading %s from cache", dest)
                return dest

        resp = http.get(url)
        if not resp.ok:
            logger.error("Issue with connecting to %s: %s", url, resp)
            if dest.exists():
                logger.warn('using unchecked %s', dest)
                return dest

        dest.write_text(resp.content)
        return dest

    def get_data(self, url):
        "Failure resistant index data loading"
        dest = self.cache / self.manifest
        dest = self.save_or_reload(url, dest)
        data = load_yaml(dest)
        data = util.packages_from_manifest(data)
        return data

    @staticmethod
    def get_data_old(session, url, cache):
        "Failure resistant index data loading"
        dest = cache / 'index.json'
        raw = None
        if dest.exists():
            raw = dest.text()
            resp = session.head(url)
            if not resp.ok:
                logger.error("Issue with connecting to %s: %s", url, resp)
                return json.loads(raw)

            if '"%s"' % dest.read_hexhash('md5') == resp.headers['etag']:
                logger.debug("loading %s from cache", dest)
                return json.loads(raw)

        resp = session.get(url)
        if not resp.ok:
            logger.error("Issue with connecting to %s: %s", url, resp)
            if dest.exists():
                logger.warn('using unchecked %s', dest)
                return json.loads(raw)

        dest.write_text(resp.content)
        return resp.json()

    def get_deps(self, dep_data, download_dir):
        with Waiter() as waiter:
            for name, (sha1, blobid)  in dep_data:
                dest = download_dir / blobid

                if dest.exists() and not dest.read_hexhash('sha1') == sha1:
                    logger.error("Bad sha1: %s", dest)
                    dest.remove()

                if dest.exists():
                    yield True, name, dest; continue

                url = '/'.join((self.index_url, blobid))
                waiter.spawn(self.download, self.http, url, dest, name, sha1)

        for status, (name, dest) in waiter.results:
            if not status:
                logger.error("Retrieval failed -- %s:%s", name, dest)
            yield name, dest

    def download(self, session, url, dest, name, sha1):
        self.dl_w_progress(session, url, dest)
        assert dest.read_hexhash('sha1') == sha1
        return name, dest

    @staticmethod
    def simple_download(session, url, dest):
        resp = session.get(url)
        if resp.ok:
            dest.write_bytes(resp.content)
            return dest

    @staticmethod
    def dl_w_progress(session, url, dest, size=1024):
        resp = session.get(url, stream=True)
        if resp.ok:
            with open(dest, 'wb') as f:
                total_length = int(resp.headers.get('content-length'))
                expected_size = (total_length/size) + 1
                for chunk in progress.bar(resp.iter_content(chunk_size=size),
                                          expected_size=expected_size):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        gevent.sleep()
            return dest

    @classmethod
    def command(cls, ctx, pargs):
        release = ctx['release']
        job = release.query_job(pargs.job)
        assert job, "Job not found"

        #@@ will need to prefix once we have more than one release

        dd = pargs.cache_dir.expanduser()
        dd.makedirs_p()

        job = pargs.job
        index_url = '/'.join((pargs.index, pargs.release_number))

        swrap = cls(index_url, release, cache=dd)
        jobob = release.query_job(job)
        results = [x for x in swrap.resolve_deps(jobob)]

        failed = [x[1] for x in results if not x[0]]
        if len(failed):
            logger.error('Files missing for %s', failed)
            return 1

        od = pargs.output_dir
        if not od.exists():
            od.makedirs()

        pkg_dir = od / 'packages'
        pkg_dir.mkdir_p()

        for name, fp in ((y, z) for x, y, z in results):
            dest = pkg_dir / name
            fp.copy(dest)

        jobout = od / 'job'
        if jobout.exists():
            jobout.rmtree()

        jobob.copytree(jobout)
        return 0

command = ShrinkWrap.command
