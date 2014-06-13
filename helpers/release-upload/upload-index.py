#!/usr/bin/python
"""
Uploads the index.json with correct Content-Type and acl for a release
"""
from boto import connect_s3
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('release', help="Release",
                        type=str)

    parser.add_argument('--bucket', help="Bucket",
                        type=str, default='cf-compiled-packages')

    pargs = parser.parse_args()
    cxn = connect_s3()
    bucket = cxn.get_bucket(pargs.bucket)
    key = bucket.get_key('%s/index.json' % pargs.release)
    key.set_metadata('Content-Type', 'application/json')

    key.set_contents_from_filename('index.json')
    key.set_acl('public-read')
    return 0

if __name__ == "__main__":
    main()
