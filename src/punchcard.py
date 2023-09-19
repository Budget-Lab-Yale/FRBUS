import os
import pandas
import numpy
import csv
import sys

from pandas import DataFrame, Period, PeriodIndex, read_csv
from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from typing import Union


# IO VERSION (probably unused)
def punchcard(filename: str) -> DataFrame:
    return(pandas.read_csv(filename, index_col=0))

def ybl_load_data(version: str, vintage: str) -> DataFrame:
    guide = os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(version), str(vintage), "LONGBASE.TXT")
    return load_data(guide)

def ybl_Frbus(version: str, vintage: str) -> Frbus:
    guide = os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(version), str(vintage),"model.xml")
    return Frbus(guide)

def run_out(card: DataFrame, stamp: str, run: int, baseline: DataFrame, sim: DataFrame):
    # Create base path 
    path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS", 
        str(card.loc[run, "version"]), stamp, card.loc[run, "ID"])
    # Check if path exists, create if it doesn't 
    if not os.path.exists(path):
        os.makedirs(path)
    # Write
    baseline.to_csv(os.path.join(path, "base-"+card.loc[run, "ID"]+".csv"))
    sim.to_csv(os.path.join(path, "sim-"+card.loc[run, "ID"]+".csv"))
    return()
