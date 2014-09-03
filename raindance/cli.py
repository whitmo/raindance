from .release import Release
from clint import resources
from path import path
from subparse import CLI
import tempfile
import logging
import sys


default_bucket = 'cf-compiled-packages'
s3_url = "http://{}.s3-website-us-east-1.amazonaws.com".format


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
                        default=s3_url(default_bucket))

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


@cli.command('raindance.pipeline:update_release_manifest')
def update_release_manifest(parser):
    parser.add_argument('-b', '--bucket', action='store',
                        help="bucket for index",
                        default=default_bucket)

    parser.add_argument('specifier', help="{software}/{version}-{arch}",
                        type=str)


main = cli.run

if __name__ == "__main__":
    sys.exit(main())
