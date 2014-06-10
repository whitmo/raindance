from functools import partial
from util import filepath
import path
import util
import re

spec_val = partial(util.submap_value, 'spec')


class Job(path.path):
    spec = filepath('spec', util.load_yaml)
    packages = spec_val('packages')
    properties = spec_val('properties')
    template_map = spec_val('templates')

    match_erb = re.compile('.*<\%(.*)\%>.*', re.MULTILINE)

    monit = filepath('monit')
    templates = filepath('templates')

    @property
    def erb_vars(self):
        files = (self / 'templates').files()
        for tmplt in files:
            name = str(tmplt.basename())
            text = tmplt.text()
            match_iter = self.match_erb.finditer(text)
            out = [x.groups()[0].strip() for x in match_iter]
            if len(out):
                yield name, out


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
