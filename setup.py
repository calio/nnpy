import os
from setuptools import setup
from subprocess import check_call
import setuptools.command.build_ext
import setuptools.command.build_py


def build_nanomsg_lib():
    check_call("bash build_nanomsg.sh", shell=True)

class BuildPyCommand(setuptools.command.build_py.build_py):
    def run(self):
        build_nanomsg_lib()
        super(BuildPyCommand, self).run()

class BuildExtCommand(setuptools.command.build_ext.build_ext):
    """Build nng library before anything else."""
    def run(self):
        build_nanomsg_lib()
        super(BuildExtCommand, self).run()

setup(
    name='nnpy-bundle',
    version='1.4.2',
    url='https://github.com/nanomsg/nnpy',
    license='MIT',
    author='Dirkjan Ochtman',
    author_email='dirkjan@ochtman.nl',
    description='cffi-based Python bindings for nanomsg',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    packages=['nnpy'],
    setup_requires=["cffi>=1.0.0"],
    cffi_modules=["generate.py:ffi"],
    install_requires=['cffi'],
)
