#!/usr/bin/env python

from distutils.core import setup

setup(name='braindump',
      version='0.2.1',
      description='Context Based Task Manager',
      author='Darren Hart',
      author_email='darren@dvhart.com',
      url='http://dvhart.com/content/projects/braindump',
      packages=['braindump', 'braindump.gui'],
#      package_data={'braindump': '__init__.py'},
      package_dir={'braindump': ''},
      data_files=[('share/braindump/images', ["images/countdown-00.png",
                                              "images/countdown-01.png",
                                              "images/countdown-02.png",
                                              "images/countdown-03.png",
                                              "images/countdown-04.png",
                                              "images/countdown-05.png",
                                              "images/countdown-06.png",
                                              "images/countdown-07.png",
                                              "images/countdown-08.png",
                                              "images/countdown-09.png",
                                              "images/countdown-10.png",
                                              "images/countdown-11.png",]),
                  ('share/braindump/glade', ['glade/braindump.glade'])],
      scripts=['braindump'],
     )

