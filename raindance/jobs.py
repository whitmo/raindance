
def jobs(release, sub='jobs'):
    return sorted((pargs.p / sub).dirs())


def show_job(pargs, path='jobs'):
    jobs_ = jobs(pargs.releasepath)

    if pargs.fullpath:
        print(json.dumps(jobs_, indent=4))
    else:
        print(json.dumps([x.basename() for x in jobs_], indent=4))
    return 0



# 'compiled_package_cache/'
# 'compiled-packages'


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()


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
