from .release import Job
from functools import partial
import json


jdump = partial(json.dumps, indent=2)


def print_jobs(ctx, pargs):
    release = ctx['release']
    joblist = sorted([str(x.basename()) for x in release.jobs.dirs()])
    print(jdump(joblist))
    return 0


def print_erb_tags(ctx, pargs):
    release = ctx['release']
    if pargs.job == 'all':
        jobs = [Job(jpath) for jpath in sorted(release.jobs.dirs())]
    else:
        jobs = [release.query_job(pargs.job)]
    allvars = {str(job.basename()): [x for x in job.erb_vars] for job in jobs}
    print(jdump(allvars))
    return 0


def print_spec(ctx, pargs):
    release = ctx['release']
    jobdata = release.query_job(pargs.name)
    spec = jobdata.spec.copy()
    attrs = ['properties', 'packages', 'templates']
    filter_by = [x for x in attrs if getattr(pargs, x)]
    if any(filter_by):
        spec = {attr:spec[attr] for attr in filter_by}
    print(jdump(spec))
