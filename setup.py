# from distutils.core import setup
from setuptools import setup

requirements=[
    'kubernetes',
	'azure'
]

setup(
	name='cloudhunky',
	install_requires=requirements,
)