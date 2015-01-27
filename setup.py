#!/usr/bin/env python

from setuptools import setup

setup(name='Sergent',
      version='1.2.2',
      description='Python Ssh to AWS EC2 helper',
      author='Nicolas Baccelli',
      author_email='nicolas.baccelli@gmail.com',
      url='',
      packages=['sergent',],
      scripts=['scripts/sergent'],
      install_requires=[
          'boto==2.35',
          'click==3.3',
          'paramiko==1.15.2'
      ],
     )