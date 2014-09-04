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


class Release(path.path):
    job_ctor = Job
    packages = filepath('packages')
    releases = filepath('releases')
    jobs = filepath('jobs')

    @property
    def joblist(self):
        return (self.job_ctor(x) for x in self.jobs.dirs())
