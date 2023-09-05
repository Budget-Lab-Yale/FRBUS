from setuptools import setup

from YBL-FRBUS-Extensions import __version__

setup(
  name="YBL-FRBUS-Extensions",
  version = __version__,
  install_requires=[
        "pandas",
        "scipy",
        "numpy",
        "black",
        "flake8",
        "mypy",
        "typing_extensions",
        "scikit-umfpack",
        "multiprocess",
        "sympy==1.3",
        "symengine",
        "matplotlib",
        "lxml",
        "networkx",
        "pyfrbus",
  ],
  packages=["YBL-FRBUS-Extensions"],
)
