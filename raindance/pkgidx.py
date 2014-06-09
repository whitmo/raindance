from boto.exception import S3ResponseError
from path import path
import json
import logging
import s3po
import sys
import gevent
import operator


logger = logging.getLogger(__name__)


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
                batch.upload(bucket_name, key, ppath.text())
