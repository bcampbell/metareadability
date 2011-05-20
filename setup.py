#!/usr/bin/env python

from distutils.core import setup

setup(name='metareadabilty',
    version='0.1',
    description='Extract headline, byline and date from articles in html',
    author='Ben Campbell',
    author_email='ben@scumways.com',
    url='http://github.com/bcampbell/metareadability',
    packages=['metareadabilty'],
    #long_description=open("README.txt").read(),
    license="GNU Affero General Public License v3",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Web Environment",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Topic :: Internet :: WWW/HTTP",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)

