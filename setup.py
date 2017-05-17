#!/usr/bin/env python3

from setuptools import find_packages, setup

if __name__ == "__main__":
    setup(name='NexisCrawler',
          version='0.1',
          maintainer='Lasse Schuirmann',
          maintainer_email='lasse.schuirmann@gmail.com',
          packages=find_packages(),
          install_requires=['PyPrint', 'PyVirtualDisplay', 'selenium'],
          entry_points={'console_scripts': ['crawl_nexis = nexis_db.cmd:main']})
