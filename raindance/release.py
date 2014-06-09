from functools import partial
from util import filepath
import path
import util


spec_val = partial(util.submap_value, 'spec')


class Job(path.path):
    spec = filepath('spec', util.load_yaml)
    monit = filepath('monit')
    templates = filepath('templates')

    name = spec_val('name')
    packages = spec_val('packages')
    properties = spec_val('properties')
    templates = spec_val('templates')


class Release(path.path):
    job_ctor = Job
    packages = filepath('packages')
    releases = filepath('releases')
    jobs = filepath('jobs')

    def query_job(self, job):
        job_p = self.jobs / job
        if not job_p.exists():
            return None
        return self.job_ctor(job_p.abspath())
