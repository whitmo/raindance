from boto.exception import S3ResponseError
#from contextlib import closing
from path import path
import gevent
import gevent.monkey
import json
import logging
import operator
import grequests
import s3po
import sys

gevent.monkey.patch_all()

logger = logging.getLogger(__name__)


def deps_command(ctx, pargs):
    release = ctx['release']
    job = release.query_job(pargs.name)
    assert job, "Job not found"
    dd = pargs.download_dir.expanduser()
    dd.makedirs_p()

    rsession = grequests.Session()
    resp = rsession.get(pargs.index)

    assert resp.ok, "Issue with connecting to %s: %s" %(pargs.index, resp)
    data = resp.json()

    dep_data = [(pkg, data[pkg]) for pkg in job.packages]
    greenlets = []
    for name, data in dep_data:
        url = '/'.join((pargs.index, data['filename']))
        g = gevent.spawn(download, rsession, url, data['filename'],
                         data['sha1'], dd)
        greenlets.append(g)
    gevent.wait(greenlets)


def download(session, url, filename, sha1, outputdir):
    dest = outputdir / filename
    worked = False
    if not dest.exists():
        resp = session.get(url, stream=True)
        if resp.ok:
            dest.write_text(resp.content)
        assert dest.read_hexhash('sha1') == sha1
        worked = True
    return worked, dest




        # #with closing(session.get(url, stream=True)) as resp, fp:
        # session.get(url, stream=True)
        # with fp:
        #     written = 0
        #     for chunk in resp.iter_content():
        #         fp.write(chunk)
        #         written += len(chunk)
        #         gevent.sleep(0)
        #         if written == resp.headers['content-length']:
        #             break




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

    cxn.upload(pargs.bucket, key, manifest)


def make_manifest_data(paths):
    mani_data = {p.name.rsplit('-', 1)[0]:dict(filename=p.name,
                                               sha1=p.read_hexhash('sha1'))
                 for p in paths}
    return mani_data


sget = operator.attrgetter('size')


def s3upload_dir(cxn, bucket_name, directory, prefix='', poolsize=200):
    bucket = cxn.conn.get_bucket(bucket_name)
    files = sorted(directory.files(), key=sget, reverse=True)
    with cxn.batch(poolsize) as batch:
        for ppath in files:
            key = '%s%s' % (prefix, ppath.basename())
            s3key = bucket.new_key(key)
            if not s3key.exists():
                logger.debug("queue file: %s -> %s", ppath, key)
                batch.upload(bucket_name, key, ppath.bytes())
