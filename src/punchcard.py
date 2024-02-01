import os
import pandas
import numpy
import csv
import sys

from pandas import DataFrame, Period, PeriodIndex, read_csv
from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from typing import Union

def parse_tax_sim(card: DataFrame, run: int, base = False) -> DataFrame:
    version = str(card.loc[run, "ts_version"])
    vintage = str(card.loc[run, "ts_vintage"])
    if(base):
        ts_id = "baseline/static"
    else:
        ts_id = str(card.loc[run, "ts_id"]) + "/conventional"

    #ts = pandas.read_csv(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator", version, vintage, ts_id, "totals/1040.csv"), index_col = 0)
    ts = pandas.read_csv(os.path.join("/vast/palmer/scratch/sarin/jar335/Tax-Simulator", version, vintage, ts_id, "totals/receipts.csv"), index_col = 0)

    ts.index = pandas.PeriodIndex(ts.index, freq="Y")

    ts['iit_etr'] = ts['revenues_income_tax'] - ts['outlays_tax_credits'] + ts['revenues_income_tax']
    
    return(ts)

def parse_corp_mtr(card: DataFrame, run: int) -> DataFrame:
    version = str(card.loc[run, "ts_version"])
    vintage = str(card.loc[run, "ts_vintage"])

    cs = pandas.read_csv(os.path.join("/vast/palmer/scratch/sarin/jar335/Tax-Simulator", version, vintage, "static/supplemental/tax_law.csv"), index_col = 0)
    cs = cs.loc["filing_status" == 1, "corp.rate"]
    
    cs.index = pandas.PeriodIndex(cs.index, freq="Y")
    return(cs)

def read_macro(path: str):
    base = pandas.read_csv(os.path.join(path, "historical.csv"), index_col=0)
    proj = pandas.read_csv(os.path.join(path, "projections.csv"), index_col=0)

    out = base.append(proj)
    out.index = pandas.PeriodIndex(out.index, freq="Y")
    
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

