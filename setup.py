#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" distribute- and pip-enabled setup.py for physio """

from distribute_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

import os, re, sys


def parse_requirements(file_name):
    requirements = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'(\s*#)|(\s*$)', line):
            continue
        if re.match(r'\s*-e\s+', line):
            requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1', line))
        elif re.match(r'\s*-f\s+', line):
            pass
        else:
            requirements.append(line)

    return requirements


def parse_dependency_links(file_name):
    dependency_links = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'\s*-[ef]\s+', line):
            dependency_links.append(re.sub(r'\s*-[ef]\s+', '', line))

    return dependency_links

# def get_git_commit_id():
#     path = os.path.abspath(sys.argv[0]) # path of script
#     cmd = "git log -n 1 --pretty=format:%%H %s" % path
#     p = os.popen(cmd)
#     gcid = p.read()
#     return gcid

def get_version():
    import physio
    return physio.__version__ #'-'.join((physio.__version__, get_git_commit_id()))

setup(
    name='physio',
    
    packages = ['physio','physio/analysis','physio/clock',\
            'physio/dsp','physio/events','physio/h5',\
            'physio/plotting','physio/reports','physio/spikes',\
            'physio/summary','physio/timeseries', 'physio/tests'],
    # package_data={'pywaveclus': ['bin/*']},
    scripts=['scripts/phy.py', 'scripts/phycfg.py'],
    version = get_version(),

    include_package_data=True,

    install_requires=parse_requirements('requirements.txt'),
    dependency_links=parse_dependency_links('requirements.txt'),

    test_suite="nose.collector",
)
