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
    #---------------------------------------------------------------------
    # Reads in Tax Simulator's personal output and prepares it for computation.
    # Parameters:
    #   card   (DataFrame): Punchcard of scenario specific parameters
    #   run          (int): Row for the card dataframe.
    #   base        (bool): Flag for if the input is a baseline run
    # Returns:
    #   ts     (DataFrame): Tax Simulator output including Effective Tax Revenue
    #---------------------------------------------------------------------
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
    #---------------------------------------------------------------------
    # Reads in Tax Simulator's corporate output and prepares it for computation.
    # Parameters:
    #   card   (DataFrame): Punchcard of scenario specific parameters
    #   run          (int): Row for the card dataframe.
    # Returns:
    #   cs     (DataFrame): Tax Simulator output.
    #---------------------------------------------------------------------
    version = str(card.loc[run, "ts_version"])
    vintage = str(card.loc[run, "ts_vintage"])
    ID      = str(card.loc[run, "ID"])
    start = pandas.Period(card.loc[run, "start"], freq='Q')
    end = pandas.Period(card.loc[run, "end"], freq='Q')

    cs = pandas.read_csv(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator", version, vintage, ID, "static/supplemental/tax_law.csv"))
    cs = cs.loc[((cs["filing_status"]==1) & (cs["year"].between(start.year, end.year))), "corp.rate"]

    cs = numpy.repeat(cs, 4)
    cs.index = pandas.period_range(start = start, end = end)
    return(cs)

def read_macro(path: str):
    #---------------------------------------------------------------------
    # Reads in macroeconomic projections.
    # Parameters:
    #   path           (path): Location of 
    # Returns:
    #   macro     (DataFrame): Tax Simulator output including Effective Tax Revenue
    #---------------------------------------------------------------------
    base = pandas.read_csv(os.path.join(path, "historical.csv"), index_col=0)
    proj = pandas.read_csv(os.path.join(path, "projections.csv"), index_col=0)

    out = base.append(proj)
    out.index = pandas.PeriodIndex(out.index, freq="Y")
    
    return(out)

def get_housing_subsidy_rates(card: DataFrame, run: int):
    start = pandas.Period(card.loc[run, "start"], freq='Q')
    end = pandas.Period(card.loc[run, "end"], freq='Q')
    outroot = os.path.join('/gpfs/gibbs/project/sarin/shared/model_data/Tax-Simulator', str(card.loc[run, "ts_version"]), str(card.loc[run, "ts_vintage"]))
    out = DataFrame(columns=["base","scen"])

    for y in pandas.period_range(start.asfreq("Y"), end.asfreq("Y")):
        base = pandas.read_csv(os.path.join(outroot, "baseline/static/detail", str(y)+'.csv'))
        base = base.loc[:,["weight", "first_mort_int", "mtr_first_mort_int"]]

        scen = pandas.read_csv(os.path.join(outroot, str(card.loc[run, "ID"]), "static/detail", str(y)+'.csv'))
        base["scen"] = scen.loc[:,"mtr_first_mort_int"]

        base = base[(abs(base["mtr_first_mort_int"]) < 2) & (abs(base["scen"]) < 2)]
        
        add = [numpy.average(base.loc[:,"mtr_first_mort_int"], weights = (base.loc[:,"weight"] * base.loc[:,"first_mort_int"])),\
            numpy.average(base.loc[:,"scen"], weights = (base.loc[:,"weight"] * base.loc[:,"first_mort_int"]))]
        out.loc[len(out.index)] = add
    
    out = out.iloc[numpy.repeat(numpy.arange(len(out)),4)]
    out *= -100
    out.index = pandas.period_range(start = start, end = end)
    return(out)

def nipa_scalar(card: DataFrame, run: int):
    tots = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/NIPA", str(card.loc[run, "nipa_vintage"]), "3-1.csv"))
    snl = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/NIPA", str(card.loc[run, "nipa_vintage"]), "3-3.csv"))
    return(1 + numpy.mean(snl.loc[Period("2009Q2", freq="Q"):Period("2019Q4", freq="Q"), "personal-current-taxes"] / tots.loc[Period("2009Q2", freq="Q"):Period("2019Q4", freq="Q"),"personal-current-taxes"]))

def run_out(card: DataFrame, stamp: str, run: int, data: DataFrame, path = None, run_type="baseline"):
    # Create base path 

    if path is not None:
        path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS", stamp)
        
        if not os.path.exists(path):
            os.makedirs(path)

    if run_type == "baseline":
        data = data.filter(regex="^((?!_).)*$")
        
        longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))
        longbase.loc[start:end,:] = data.loc[start:end,:]
        longbase.to_csv(os.path.join(path,card.loc[run,"ID"]+"_LONGBASE.csv"))
    
    return()

