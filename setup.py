from setuptools import setup

from YBL_FRBUS_Extensions import __version__

setup(
  name="YBL_FRBUS_Extensions",
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
  packages=["YBL_FRBUS_Extensions"],
)
