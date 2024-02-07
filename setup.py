from setuptools import setup

setup(
  name="YBL-FRBUS",
  version = "dev",

  url='https://github.com/Budget-Lab-Yale/FRBUS',
  author='Yale Budget Lab',
  
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
