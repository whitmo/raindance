#from contextlib import closing
from boto.exception import S3ResponseError
from clint import resources
from clint.textui import progress
from path import path
import gevent
import gevent.monkey
import grequests
import json
import logging
import operator
import s3po
import sys

gevent.monkey.patch_all()

logger = logging.getLogger(__name__)


def deps_command(ctx, pargs):
    release = ctx['release']
    job = release.query_job(pargs.name)
    assert job, "Job not found"
    dd = pargs.cache_dir.expanduser()
    dd.makedirs_p()

    rsession = grequests.Session()
    resp = rsession.get(pargs.index)

    assert resp.ok, "Issue with connecting to %s: %s" %(pargs.index, resp)
    data = resp.json()

    dep_data = [(pkg, data[pkg]) for pkg in job.packages]
    print json.dumps([x for x in get_deps(rsession, pargs.index, dep_data, dd)], indent=2)


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






def upload_compiled_packages(ctx, pargs):
    from gevent import monkey
    monkey.patch_all()
    creds = pargs.access_key, pargs.secret_key

    assert all(creds), "Missing AWS Credentials: a: '%s', s:'%s'" % creds
    cxn = s3po.Connection(*creds)

    if pargs.create:
        try:
            cxn.conn.get_bucket(pargs.bucket)
        except S3ResponseError:
            cxn.conn.create_bucket(pargs.bucket)

    cache = path(pargs.packages)
    files = cache.files()
    logger.debug("-- %s files --", len(files))

    if not pargs.manifest_only:
        s3upload_dir(cxn, pargs.bucket, cache,
                     prefix=pargs.prefix)

    mani_data = make_manifest_data(cache.files())
    manifest = json.dumps(mani_data, indent=4)

    key = pargs.prefix and \
      "%s%s" % (pargs.prefix, 'index.json') or 'index.json'

    cxn.upload(pargs.bucket, key, manifest, headers={'Content-Type':'application.json'})
    return 0


def make_manifest_data(paths):
    mani_data = {p.name.rsplit('-', 1)[0]:dict(filename=p.name,
                                               sha1=p.read_hexhash('sha1'))
                 for p in paths}
    return mani_data


sget = operator.attrgetter('size')


def s3upload_dir(cxn, bucket_name, directory, prefix='', poolsize=200):
    bucket = cxn.conn.get_bucket(bucket_name)
    files = sorted(directory.files(), key=sget, reverse=True)
    headers = {'Content-Type':'application/x-tar'}
    with cxn.batch(poolsize) as batch:
        for ppath in files:
            key = '%s%s' % (prefix, ppath.basename())
            s3key = bucket.new_key(key)
            if not s3key.exists():
                logger.debug("queue file: %s -> %s", ppath, key)
                batch.upload(bucket_name, key, ppath.bytes(), headers=headers)
