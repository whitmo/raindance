from .release import Release
from clint import resources
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
    resources.init('cf-charmers', 'raindance')
    parser.add_argument('-p', '--releasepath', action='store',
                        help="path to cf-release",
                        type=path,
                        default=path('.').abspath() / 'cf-release')

    index_url = 'http://cf-compiled-packages.s3-website-us-east-1.amazonaws.com'
    parser.add_argument('-i', '--index', action='store',
                        help="URL of compiled package index",
                        default=index_url)

    parser.add_argument('-n',  '--release-number', action='store', default=None,
                        help="Release number")


cli = CLI(version='0.0', context_factory=make_context)
cli.add_generic_options(genopts)


@cli.command('raindance.shrinkwrap:command')
def shrinkwrap(parser):
    """
    List the all jobs
    """
    parser.add_argument('name', help="job to shrinkwrap",
                        type=str)

    parser.add_argument('output_dir', help="directory to populate",
                        type=path)

    cache = path(resources.user.path) / 'cpkg-cache'
    parser.add_argument('--cache-dir',
                        help="Download directory for job dependencies",
                        action='store', default=cache)

    parser.add_argument('--dryrun',
                        help="Check deps and availability, but do nothing",
                        action='store_true', default=False)


@cli.command('raindance.job:print_erb_tags')
def erb(parser):
    """
    Explore erb tags in job templates
    """
    parser.add_argument('-s', '--erb-tags', help="show erb tags",
                        action='store_true', default=False)

    parser.add_argument('job', help="show erb tags")
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


main = cli.run

if __name__ == "__main__":
    sys.exit(main())
