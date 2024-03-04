from setuptools import setup

setup(
  name="FRBUS",
  version = "1.0",
  author='Yale Budget Lab',  
  install_requires=[
        "pandas",
        "scipy",
        "numpy",
        "black",
        "flake8",
        "mypy",
        "typing_extensions",
        "multiprocess",
        "sympy==1.3",
        "symengine",
        "matplotlib",
        "lxml",
        "networkx",
        "scikit-umfpack==0.3.3",
        "pyfrbus",
  ],
  packages=["FRBUS"],
)
