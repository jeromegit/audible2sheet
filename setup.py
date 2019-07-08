# -*- coding: utf-8 -*-

# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='audible2sheet',
    version='0.1.0',
    description='Script to export the list of books in one\'s Audible library into a Google Sheet document',
    long_description=readme,
    author='Jerome Provensal',
    author_email='jerome@provensal.com',
    url='https://github.com/jeromegit/audible2sheet',
    license=license,
    entry_points={
        'console_scripts': [
            'audible2sheet=audible2sheet:main',
        ]
    },
    packages=find_packages(exclude=('tests', 'docs'))
)

