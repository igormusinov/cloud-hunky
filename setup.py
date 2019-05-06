# from distutils.core import setup
from setuptools import setup

requirements=[
    'kubernetes',
	'azure'
]

setup(
	name='k8scontroller',
	install_requires=requirements,
)