import setuptools
from setuptools import setup

setup(
    name="pyPUMA",
    version="0.0.1",
    author="Range, Jan",
    author_email="jan.range@simtech.uni-stuttgart.de",
    license="BSD2 Clause",
    packages=setuptools.find_packages(),
    install_requires=[
      "pydantic",
      "dictdiffer",
      "pandas",
    ]
)
