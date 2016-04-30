#!/usr/bin/env python

PROJECT = 'wcscalendar'

VERSION = '0.1'

from setuptools import setup, find_packages

try:
    long_description = open('README.rst', 'rt').read()
except IOError:
    long_description = ''

setup(
    name=PROJECT,
    version=VERSION,

    description='WCS Calendar parse official Blizzard WCS schedule '
                'and fills Google Calendar',
    long_description=long_description,

    author='Mykola Yakovliev',
    author_email='vegasq@gmail.com',

    url='https://github.com/vegasq/wcscalendar',
    download_url='https://github.com/vegasq/wcscalendar',

    classifiers=['Development Status :: 3 - Alpha',
                 'License :: OSI Approved :: Apache Software License',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.2',
                 'Intended Audience :: Developers',
                 'Environment :: Console',
                 ],

    platforms=['Any'],

    scripts=[],

    provides=[],
    install_requires=['cliff',
                      'google-api-python-client'],

    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'wcscalendar = WCSCalendar.wcsc:main'
        ],
        'cliff.demo': [
            'simple = cliffdemo.simple:Simple',
            'two_part = cliffdemo.simple:Simple',
            'error = cliffdemo.simple:Error',
            'list files = cliffdemo.list:Files',
            'files = cliffdemo.list:Files',
            'file = cliffdemo.show:File',
            'show file = cliffdemo.show:File',
            'unicode = cliffdemo.encoding:Encoding',
        ],
    },

    zip_safe=False,
)
