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
        ID = "baseline/static"
    else:
        ID = str(card.loc[run, "ID"]) + "/conventional"

    ts = pandas.read_csv(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator", version, vintage, ID, "totals/receipts.csv"), index_col = 0)
    #ts = pandas.read_csv(os.path.join("/vast/palmer/scratch/sarin/jar335/Tax-Simulator", version, vintage, ID, "totals/receipts.csv"), index_col = 0)
    ts.index = pandas.PeriodIndex(ts.index, freq="Y")

    ts['iit_etr'] = ts.loc[:,'revenues_income_tax'] - ts.loc[:,'outlays_tax_credits'] + ts.loc[:,'revenues_estate_tax']
    
    return(ts)

def parse_corp_mtr(card: DataFrame, run: int) -> DataFrame:
    version = str(card.loc[run, "ts_version"])
    vintage = str(card.loc[run, "ts_vintage"])
    ID      = str(card.loc[run, "ID"])

    cs = pandas.read_csv(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator", version, vintage, ID, "static/supplemental/tax_law.csv"))
    cs = cs.loc[cs["filing_status"] == 1, ["year", "corp.rate"]]
    
    cs.set_index('year', inplace=True)
    cs.index = pandas.PeriodIndex(cs.index, freq="Y")
    return(cs)

def read_macro(path: str):
    base = pandas.read_csv(os.path.join(path, "historical.csv"), index_col=0)
    proj = pandas.read_csv(os.path.join(path, "projections.csv"), index_col=0)

    out = base.append(proj)
    out.index = pandas.PeriodIndex(out.index, freq="Y")
    
    return(out)

def get_housing_subsidy_rates(card: DataFrame, run: int):
    start = pandas.Period(card.loc[run, "start"], freq='Y')
    end = pandas.Period(card.loc[run, "end"], freq='Y')
    outroot = os.path.join('/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator', str(card.loc[run, "ts_version"]), str(card.loc[run, "ts_vintage"]))
    out = DataFrame(columns=["base","scen"])

    for y in pandas.period_range(start, end):
        base = pandas.read_csv(os.path.join(outroot, "baseline/static/detail", str(y)+'.csv'))
        base = base.loc[:,["weight", "first_mort_int", "mtr_first_mort_int"]]

        scen = pandas.read_csv(os.path.join(outroot, str(card.loc[run, "ID"]), "static/detail", str(y)+'.csv'))
        base["scen"] = scen.loc[:,"mtr_first_mort_int"]
        
        add = [numpy.average(base.loc[:,"mtr_first_mort_int"], weights = (base.loc[:,"weight"] * base.loc[:,"first_mort_int"])),\
            numpy.average(base.loc[:,"scen"], weights = (base.loc[:,"weight"] * base.loc[:,"first_mort_int"]))]
        out.loc[len(out.index)] = add
    
    out.index = pandas.period_range(start = start, end = end)
    return(out)

def run_out(card: DataFrame, stamp: str, run: int, data: DataFrame):
    # Create base path 
    path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS", card.loc[run, "version"], stamp, card.loc[run, "ID"])
    # Check if path exists, create if it doesn't 
    if not os.path.exists(path):
        os.makedirs(path)
    # Write
    data.to_csv(os.path.join(path, "base-"+card.loc[run, "ID"]+".csv"))
    #sim.to_csv(os.path.join(path, "sim-"+card.loc[run, "ID"]+".csv"))
    return()

