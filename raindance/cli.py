from path import path
import argparse
import sys
import json
import yaml
import s3po


def jobs(release, sub='jobs'):
    return sorted((pargs.p / sub).dirs())


def show_job(pargs, path='jobs'):
    jobs = jobs(pargs.releasepath)

    if pargs.fullpath:
        print(json.dumps(jobs, indent=4))
    else:
        print(json.dumps([x.basename() for x in jobs], indent=4))
    return 0


def upload_compiled_packages(pargs):
    from gevent import monkey
    monkey.patch_all()
    cxn = s3po.connection(pargs.access_key, pargs.secret_key)
    cache = path(pargs.packages)
    paths = [x for x in s3upload_dir(cxn, pargs.bucket,
                               cache, prefix=pargs.prefix)]

    mani_data = make_manifest_data(paths)
    manifest = json.dumps(mani_data, pargs.pretty)

    key = pargs.prefix and \
      "%s%s" % (pargs.prefix, 'index.json') or 'index.json'

    cxn.upload(pargs.bucket, key, manifest)


def make_manifest_data(prefix, paths):
    mani_data = {p.name.rsplit('-', 1): (p.name,
                                         p.read_hexhash('sha1'))
                 for p in paths}
    return mani_data


def s3upload_dir(cxn, bucket, directory, prefix='', poolsize=50):
    with cxn.batch(poolsize) as batch:
        for ppath in directory.files():
            key = '%s%s' % (prefix, ppath.basename())
            batch.upload(bucket, key, ppath.text())
            yield ppath, ppath.read_hashhex('sha1')

# 'compiled_package_cache/'
# 'compiled-packages'


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--releasepath', action='store',
                        help="path to cf-release",
                        default=path('.').abspath() / 'cf-release')



    parser.add_argument('-n', action='store', default=None,
                        help="Release number")

    subs = parser.add_subparsers(help='commands')

    jobs_p = subs.add_parser('job', help='Job related functions')
    jobs_p.add_argument('--fullpath', '-f', action='store', default=False)
    jobs_p.set_defaults(func=show_job)

    charmable_p = subs.add_parser('charmable', help='Job related functions')
    charmable_p.add_argument('-m', '--manifest', action='store',
                        help="path to package manifest",
                        default=path('.').abspath() / 'manifest.yml')
    charmable_p.set_defaults(func=charmable)


    pargs = parser.parse_args(args=args)
    return pargs.func(pargs)



if __name__ == "__main__":
    sys.exit(main())
