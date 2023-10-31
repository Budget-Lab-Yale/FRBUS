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

def parse_tax_sim(card: DataFrame, run: int) -> DataFrame:
    version = str(card.loc[run, "ts_version"])
    vintage = str(card.loc[run, "ts_vintage"])
    ts_id   = str(card.loc[run, "ID"])

    ts_1040 = pandas.read_csv(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator", version, vintage, ts_id, "static/totals/1040.csv"), index_col = 0)

    ts_pr = pandas.read_csv(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator", version, vintage, ts_id, "static/totals/payroll.csv"), index_col = 0)

    ts = ts_1040.merge(ts_pr, how = 'left')
    ts.index = pandas.PeriodIndex(ts.index, freq="Q")

    ts.rename(columns={"liab_iit_":"gtn"})
    ts["trp"] = ts[["liab_iit"]] / ts[["txbl_inc"]]
    ts["trfpm"] = calc_marginal(card, run)
    
    return(ts[["gtn", "trp", "trfpm"]])

def calc_marginal(card: DataFrame, run: int):

    version = str(card.loc[run, "ts_version"])
    vintage = str(card.loc[run, "ts_vintage"])
    ts_id   = str(card.loc[run, "ID"])

    micro_path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator", version, vintage, ts_id, "static/detail")
    out = numpy.array()

    for filename in os.listdir(micro_path, 'files'):
        micro = pandas.read_csv(os.path.join(micro_path, filename))
        micro.sort_values(by=['agi'])
        micro["csum_wgt"] = numpy.cumsum(micro["weight"]/sum(micro["weight"]))
        temp = micro[micro.csum_wgt >= 0.5]
        out.append(brackets(temp.head(1)))
    
    return(out)

def brackets(fam: DataFrame):
    # NOT USED MOST LIKELY

    threshs = numpy.array(
        [[11000, 44725, 95375,182100,231250,578125],
        [22000,89450,190750,364200,462500,693750],
        [11000, 44725, 95375,182100,231250,578125],
        [15700,59850,95650,182100,231250,578100,578101]
        ]
    )
    dex = fam["filing_status"]-1
    med2 = fam["txbl_inc"] * 2

    if(med2 <= threshs[dex, 0]):
        return(10)
    elif(med2 <= threshs[dex, 1]):
        return(12)
    elif(med2 <= threshs[dex, 2]):
        return(22)
    elif(med2 <= threshs[dex, 3]):
        return(24)
    elif(med2 <= threshs[dex, 4]):
        return(32)
    elif(med2 <= trhesh[dex, 5]):
        return(35)
    else:
        return(37)

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
