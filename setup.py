# from distutils.core import setup
from setuptools import setup

requirements=[
    'kubernetes',
	'azure==4.0.0'
]

setup(
	name='cloudhunky',
	install_requires=requirements,
)
