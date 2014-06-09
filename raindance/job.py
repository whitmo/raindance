import json


def job_command(ctx, pargs):
    pass


def print_jobs(ctx, pargs):
    release = ctx['release']
    joblist = sorted([str(x.basename()) for x in release.jobs.dirs()])
    print(json.dumps(joblist, indent=2))


def print_spec(ctx, pargs):
    release = ctx['release']
    jobdata = release.query_job(pargs.name)
    spec = jobdata.spec.copy()
    attrs = ['properties', 'packages', 'templates']
    filter_by = [x for x in attrs if getattr(pargs, x)]
    if any(filter_by):
        spec = {attr:spec[attr] for attr in filter_by}
    print(json.dumps(spec, indent=2))
