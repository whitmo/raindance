from clint.textui import progress
from functools import partial
import gevent
import gevent.monkey
import grequests
import json
import logging

gevent.monkey.patch_all()
jdump = partial(json.dumps, indent=2)
logger = logging.getLogger(__name__)


def command(ctx, pargs):
    release = ctx['release']
    job = release.query_job(pargs.name)
    assert job, "Job not found"

    #@@ will need to prefix once we have more than one release

    dd = pargs.cache_dir.expanduser()
    dd.makedirs_p()

    rsession = grequests.Session()
    data = get_data(rsession, pargs.index, dd)

    dep_data = [(pkg, data[pkg]) for pkg in job.packages]
    results = [x for x in get_deps(rsession, pargs.index, dep_data, dd)]
    print jdump(results)


def get_data(session, url, dd):
    "Failure resistant index data loading"
    dest = dd / 'index.json'
    raw = None
    if dest.exists():
        raw = dest.text()
        resp = session.head(url)
        if not resp.ok:
            logger.error("Issue with connecting to %s: %s", url, resp)
            return json.loads(raw)

        if dest.read_hexhash('md5') == resp.headers['etag']:
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


def get_deps(session, index, dep_data, download_dir):
    greenlets = []
    for name, data in dep_data:

        filename = data['filename']
        sha1 = data['sha1']
        dest = download_dir / filename

        if dest.exists() and not dest.read_hexhash('sha1') == sha1:
            logger.error("Bad sha1: %s", dest)
            dest.remove()

        if dest.exists():
            yield True, name, dest; continue

        url = '/'.join((index, filename))
        g = gevent.spawn(download, session, url, dest, name, sha1)
        greenlets.append(g)

    gevent.wait(greenlets)

    for greenlet in greenlets:
        status = greenlet.successful()
        yield status, greenlet.value
        if not status:
            logger.error("Retrieval failed -- %s:%s", name, dest)


def download(session, url, dest, name, sha1):
    dl_w_progress(session, url, dest)
    assert dest.read_hexhash('sha1') == sha1
    return name, dest


def simple_download(session, url, dest):
    resp = session.get(url)
    if resp.ok:
        dest.write_bytes(resp.content)
        return dest


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
