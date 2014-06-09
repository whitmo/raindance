from .release import Release
from path import path
from subparse import CLI
import logging
import os
import sys


def make_context(cli, args):
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    release = Release(args.releasepath)
    return dict(release=release, logger=logger)


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


@cli.command('raindance.job:job_command')
def job(parser):
    "For working with a specific job"
    parser.add_argument('name', help="directory w/ compiled packages",
                        type=str)

    parser.add_argument('-d', '--download', help="download packages for this job",
                        action="store_true",
                        default=False)

    parser.add_argument('-w', '--shrinkwrap', help="Zip up job and packages",
                        action="store_true",
                        default=False)

    return parser

@cli.command('raindance.job:print_jobs')
def jobs(parser):
    """
    List the all jobs
    """
    return parser


@cli.command('raindance.job:print_spec')
def spec(parser):
    "spec in json for a job"
    parser.add_argument('name', help="json rendering of spec",
                        type=str)

    parser.add_argument('-p', '--packages', help="show packages",
                        action='store_true', default=False)

    parser.add_argument('-t', '--templates', help="show templates",
                        action='store_true', default=False)

    parser.add_argument('-a', '--properties', help="show properties",
                        action='store_true', default=False)
    return parser


main = cli.run

if __name__ == "__main__":

    sys.exit(main())
