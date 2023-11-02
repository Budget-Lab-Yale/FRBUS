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

def parse_tax_sim(card: DataFrame, run: int, base = False) -> DataFrame:
    version = str(card.loc[run, "ts_version"])
    vintage = str(card.loc[run, "ts_vintage"])
    if(base):
        ts_id = "baseline/static"
    else:
        ts_id   = str(card.loc[run, "ts_ID"]) + "/conventional"

    ts = pandas.read_csv(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator", version, vintage, ts_id, "totals/1040.csv"), index_col = 0)

    ts.index = pandas.PeriodIndex(ts.index, freq="Q")
    
    return(ts[["liab_iit", "liab_iit_net"]])

def calc_marginal(card: DataFrame, run: int):
    # THERE IS A BETTER WAY TO GO ABOUT THIS

    version = str(card.loc[run, "ts_version"])
    vintage = str(card.loc[run, "ts_vintage"])
    ts_id   = str(card.loc[run, "ts_ID"])

    micro_path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator", version, vintage, ts_id, "static/detail")
    out = numpy.array()

    for filename in os.listdir(micro_path, 'files'):
        micro = pandas.read_csv(os.path.join(micro_path, filename))
        micro.sort_values(by=['agi'])
        micro["csum_wgt"] = numpy.cumsum(micro["weight"]/sum(micro["weight"]))
        temp = micro[micro.csum_wgt >= 0.5]
        out.append(brackets(temp.head(1)))
    
    return(out)

def run_out(card: DataFrame, stamp: str, run: int, baseline: DataFrame, sim: DataFrame):
    # Create base path 
    path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS", card.loc[run, "version"], stamp, card.loc[run, "ID"])
    # Check if path exists, create if it doesn't 
    if not os.path.exists(path):
        os.makedirs(path)
    # Write
    baseline.to_csv(os.path.join(path, "base-"+card.loc[run, "ID"]+".csv"))
    sim.to_csv(os.path.join(path, "sim-"+card.loc[run, "ID"]+".csv"))
    return()
