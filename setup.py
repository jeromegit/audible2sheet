# -*- coding: utf-8 -*-
# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages
from os import path

with open('README.md', 'r', encoding='utf-8') as readme_f:
    readme = '\n' + readme_f.read()

# get the dependencies and installs
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]
dependency_links = [x.strip().replace('git+', '') for x in all_reqs if x.startswith('git+')]

setup(
    name='audible2sheet',
    version='0.1.0',
    description='Script to export the list of books in one\'s Audible library into a Google Sheet document',
    long_description_content_type='text/x-rst',
    long_description=readme,
    author='Jerome Provensal',
    author_email='jerome@provensal.com',
    license='MIT',
    url='https://github.com/jeromegit/audible2sheet',
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'audible2sheet=audible2sheet:main',
        ]
    },
    packages=find_packages(exclude=('tests', 'docs'))
)
