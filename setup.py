#!/usr/bin/env python3

from setuptools import setup

setup(
    name='eternalegypt',
    packages=['eternalegypt'],
    version='0.0.5',
    install_requires=['aiohttp>=3.0.1','attrs'],
    description='Netgear LTE modem API',
    author='Anders Melchiorsen',
    author_email='amelchio@nogoto.net',
    url='https://github.com/amelchio/eternalegypt',
    license='MIT',
    keywords=['netgear,lte,lb1120,lb2120'],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3 :: Only",
    ],
)
