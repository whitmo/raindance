from . import pkgidx
from boto.exception import S3ResponseError
from path import path
from subparse import CLI
import logging
import os
import sys
import yaml


def make_context(cli, args):
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    return dict(logger=logger)


def genopts(parser):
    parser.add_argument('-p', '--releasepath', action='store',
                        help="path to cf-release",
                        default=path('.').abspath() / 'cf-release')

    parser.add_argument('-n', action='store', default=None,
                        help="Release number")


cli = CLI(version='0.0', context_factory=make_context)
cli.add_generic_options(genopts)


@cli.command('raindance.pkgidx:upload_compiled_packages')
def upload(parser):
    """
    Upload compiled packages to S3
    """
    env = os.environ.get
    parser.add_argument('--secret-key', help="aws secret key",
                        default=env('AWS_SECRET_KEY', ''))

    parser.add_argument('--access-key', help="aws access key",
                        default=os.environ.get('AWS_ACCESS_KEY', ''))

    parser.add_argument('packages', help="directory w/ compiled packages",
                        type=path)

    parser.add_argument('--bucket', help="s3 bucket for package upload",
                        default='cf-compiled-packages')

    parser.add_argument('--create', help="create s3 bucket if not available",
                        action='store_true',
                        default=False)

    parser.add_argument('--manifest-only', help="only upload manifest",
                        action='store_true',
                        default=False)

    parser.add_argument('--prefix', help="key prefix for package upload",
                        default="")

    return parser





main = cli.run

if __name__ == "__main__":

    sys.exit(main())
