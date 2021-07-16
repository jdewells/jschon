import pathlib
import re

from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent.resolve()
README = (HERE / 'README.md').read_text(encoding='utf-8')
VERSION = eval(re.search(
    '^__version__ = (.*)$',
    (HERE / 'jschon' / '__init__.py').read_text(encoding='utf-8'),
    re.MULTILINE,
)[1])

setup(
    name='jschon-shamelessdowngrade',
    version=VERSION,
    description='A shameless downgrade of a pythonic, extensible JSON Schema implementation.',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://github.com/jdewells/jschon',
    authors='Mark Jacobson, Jonathan Wells',
    author_email='jdewells25@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    python_requires='~=3.6',
    install_requires=['rfc3986'],
    extras_require={
        'test': [
            'tox',
        ],
        'dev': [
            'pytest',
            'coverage',
            'hypothesis',
            'pytest-benchmark',
        ],
        'doc': [
            'sphinx',
            'sphinx-rtd-theme',
        ],
    },
)
