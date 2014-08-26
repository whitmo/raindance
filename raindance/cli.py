from .release import Release
from clint import resources
from path import path
from subparse import CLI
import tempfile
import logging
import os
import sys


default_index_url = "http://cf-compiled-packages.s3-website-us-east-1.amazonaws.com"


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

    parser.add_argument('-i', '--index', action='store',
                        help="URL of compiled package index",
                        default=default_index_url)

    #@@ calculated latest release
    parser.add_argument('-n',  '--release-number', action='store',
                        default='180',
                        help="Release number")


cli = CLI(version='0.0', context_factory=make_context)
cli.add_generic_options(genopts)


@cli.command('raindance.pipeline:prep_export')
def prep_export(parser):
    """
    Rearrange exported packages for upload to juju cf release archive

    (http://cf-packages.s3-website-us-east-1.amazonaws.com)
    """
    parser.add_argument('exported_packages', help="export to upload",
                        type=path)

    tempdir = path(tempfile.mkdtemp(prefix='cf-job-artifacts-'))
    parser.add_argument('--workdir', type=path,
                        help="working directory for preparing job artefacts",
                        default=tempdir)

    parser.add_argument('--outdir', type=path,
                        help="final output directory",
                        default=tempdir / 'final')

    return parser


@cli.command('raindance.pipeline:create_artefacts')
def pack_jobs(parser):
    """
    Zip compiled packages into jobs
    """
    parser.add_argument('exported_packages', help="export to upload",
                        type=path)

    parser.add_argument('--workdir', type=path,
                        help="working directory for preparing job artefacts",
                        default=path(tempfile.mkdtemp(prefix='cf-job-artifacts-')))

    return parser


@cli.command('raindance.pipeline:upload_export')
def upload_export(parser):
    """
    Archive out original output for safekeeping
    """
    parser.add_argument('tarball', help="export to upload",
                        type=path)

    parser.add_argument('--bucket', help="s3 bucket for export upload",
                        default='cf-exported-releases')

    env = os.environ.get
    parser.add_argument('--secret-key', help="aws secret key",
                        default=env('AWS_SECRET_KEY', ''))

    parser.add_argument('--access-key', help="aws access key",
                        default=os.environ.get('AWS_ACCESS_KEY', ''))

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




@cli.command('raindance.job:print_jobs')
def jobs(parser):
    """
    List the all jobs
    """
    return parser


main = cli.run

if __name__ == "__main__":
    sys.exit(main())
