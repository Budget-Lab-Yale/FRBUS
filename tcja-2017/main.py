############### Program to construct TCJA Dyanmic Revenue Estimate ###############

### STEP 0: Load Packages & Set time stamp ###
from pandas import DataFrame, Period, PeriodIndex, read_csv
import datetime
import pyfrbus
import sys
import os
import numpy
import pandas
from numpy import array, shape, nan
from typing import Union

import matplotlib.pyplot as plt

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import  denton_boot, dynamic_rev

from punchcard import parse_tax_sim, read_gdp, parse_corp_sim


#can move into loop if we want a vintage stamp for every model run
ct = datetime.datetime.now()
stamp = str(ct.year)+str(ct.month)+str(ct.day)+str(ct.hour)

card = read_csv("/gpfs/gibbs/project/sarin/ser68/TCJA/Dynamic_rev_est/base10_card.csv")

### STEP 1A: Disaggregate Tax Sim revenue series ###

def build_data(card: DataFrame, run: int, raw = False, card_dates = False):
    #---------------------------------------------------------------------
    # This function constructs a baseline dataset using the mcontrol protocol
    # against which alternate scenario runs are compared. 
    # Parameters:
    #   card (DataFrame): Punchcard of test specific parameters
    #   run  (int)      : Row for the card dataframe. Should always be 1.
    #   raw  (bool)     : Flag for if the baseline is constructed by YBL or the FOMC
    # Returns:
    #   longbase (DataFrame): FRB longbase.txt file adjusted to suit this 
    #                         specific policy test.
    #---------------------------------------------------------------------
    if raw:
        longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))
    else:
        longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/Baselines", str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))

    ts = parse_tax_sim(card, run, True)

    if card_dates:
        start = pandas.Period(card.loc[run, "start"][0:4], freq="Y")
        end = pandas.Period(card.loc[run, "end"][0:4], freq="Y")
    else:
        start = ts.index[0]
        end = ts.index[len(ts)-1]

    cs = parse_corp_sim(card, run)
    
    cbo = read_gdp(card.loc[run, "cbo_path"])
    cbo = cbo.loc[start:end,:]
    cbo['TPN_ts'] = ts["liab_iit_net"] / cbo["gdp"]
    cbo['TCIN_cs'] = cs["TCIN"] / cbo["gdp"]

    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    temp = longbase.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = cbo.index
    cbo["TPN_ts"] *= temp
    cbo["TCIN_cs"] *= temp 

    TPN_fs = denton_boot(cbo["TPN_ts"].to_numpy())
    TCIN_fs = denton_boot(cbo["TCIN_cs"].to_numpy())

    frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")
    longbase.loc[start:end, "dfpsrp"] = 1
    longbase.loc[start:end, "dfpdbt"] = 0
    longbase.loc[start:end, "dfpex"] = 0

    longbase.loc[start-100:, 'dfpdbt'] = 0
    longbase.loc[start-100:end, 'dfpex'] = 1
    longbase.loc[start-100:end, 'dfpsrp'] = 0
    longbase.loc[end+1:, 'dfpsrp'] = 1

    longbase.loc[start:, "dmpintay"] = 1
    longbase.loc[start:, "dmptay"] = 0
    longbase.loc[start:, "dmpalt"] = 0
    longbase.loc[start:, "dmpex"] = 0
    longbase.loc[start:, "dmprr"] = 0
    longbase.loc[start:, "dmptlr"] = 0
    longbase.loc[start:, "dmptlur"] = 0
    longbase.loc[start:, "dmptmax"] = 0
    longbase.loc[start:, "dmptpi"] = 0
    longbase.loc[start:, "dmptr"] = 0
    longbase.loc[start:, "dmptrsh"] = 0

    with_adds = frbus.init_trac(start, end, longbase)
    with_adds.loc[start:end, "tpn_t"] = TPN_fs
    with_adds.loc[start:end, "tcin_t"] = TCIN_fs

    out = frbus.mcontrol(start, end, with_adds, targ=["tpn", "tcin"], traj=["tpn_t", "tcin_t"], inst=["trp_aerr", "trci_aerr"])
    out = out.filter(regex="^((?!_).)*$")

    longbase.loc[start:end,:] = out.loc[start:end,:]
    return(longbase)



#data = build_data(card, 0)
data = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/Baselines", str(card.loc[0, "lb_vintage"]), "LONGBASE.TXT"))
### STEP 1B: Load FRBUS and set parameters###

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")


### STEP 2: Interpolate CBO/JCT deltas ###

cbo_delta = read_csv("/gpfs/gibbs/project/sarin/ser68/TCJA/Dynamic_rev_est/Deltas/jct_delta.csv")

tpn_delta = (denton_boot(cbo_delta["tpn_delta"].to_numpy()))
trci_delta = (denton_boot(cbo_delta["trci_delta"].to_numpy()))

start = card.loc[0,"start"]
end = card.loc[0, "end"]

# Replace 2017 values with 0 #
tpn_delta[0:4] = 0
trci_delta[0:4] = 0

### STEP 3: Calculate Dynamic Revenue Estimate ###
start = pandas.Period(card.loc[0, "start"], freq="Q")
end = pandas.Period(card.loc[0, "end"], freq="Q")

data.loc[start:end, 'dfpdbt'] = 0
data.loc[start:end, 'dfpex'] = 0
data.loc[start:end, 'dfpsrp'] = 1

data.loc[start:, "dmpintay"] = 1
data.loc[start:, "dmptay"] = 0
data.loc[start:, "dmpalt"] = 0
data.loc[start:, "dmpex"] = 0
data.loc[start:, "dmprr"] = 0
data.loc[start:, "dmptlr"] = 0
data.loc[start:, "dmptlur"] = 0
data.loc[start:, "dmptmax"] = 0
data.loc[start:, "dmptpi"] = 0
data.loc[start:, "dmptr"] = 0
data.loc[start:, "dmptrsh"] = 0

with_adds = frbus.init_trac(start, end, data)

with_adds.loc[start:end, "tpn_d"] = tpn_delta
with_adds.loc[start:end, "tcin_d"] = trci_delta

def calc_tcin_path(card: DataFrame, run: int, data: DataFrame, card_dates = False):
    cs = parse_corp_sim(card, run)

    if card_dates:
        start = pandas.Period(card.loc[run, "start"][0:4], freq="Y")
        end = pandas.Period(card.loc[run, "end"][0:4], freq="Y")

    else:
        start = cs.index[0]
        end = cs.index[len(cs)-1]

    cbo = read_gdp(card.loc[run, "cbo_path"])
    cbo = cbo.loc[start:end]
    cbo['TCIN_cs'] = cs["TCIN"] / cbo["gdp"]

    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    temp = data.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = cbo.index
    cbo["TCIN_cs"] *= temp

    TCIN_fs = (denton_boot(cbo["TCIN_cs"].to_numpy()))
    
    return(TCIN_fs)

def calc_tpn_path(card: DataFrame, run: int, data: DataFrame, card_dates = False):
    ts = parse_tax_sim(card, run, False)
    
    if card_dates:
        start = pandas.Period(card.loc[run, "start"][0:4], freq="Y")
        end = pandas.Period(card.loc[run, "end"][0:4], freq="Y")
    
    else:
        start = ts.index[0]
        end = ts.index[len(ts)-1]

    cbo = read_gdp(card.loc[run, "cbo_path"])
    cbo = cbo.loc[start:end]
    cbo['TPN_ts'] = ts["liab_iit_net"] / cbo["gdp"]
    
    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    temp = data.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = cbo.index
    cbo["TPN_ts"] *= temp

    TPN_fs = (denton_boot(cbo["TPN_ts"].to_numpy()))
    
    return(TPN_fs)



cbo = read_gdp(card.loc[0, "cbo_path"])
start_cbo = pandas.Period(str(start.year), freq="Y")
end_cbo = pandas.Period(str(end.year), freq="Y")


with_adds.loc[start:end, "trp_t"] = ((with_adds.loc[start:end, "tpn_d"] + calc_tpn_path(card, 0, with_adds, True)) / (with_adds.loc[start:end, "ypn"] - with_adds.loc[start:end, "gtn"]))
with_adds.loc[start:end, "trci_t"] = (with_adds.loc[start:end, "tcin_d"] + calc_tcin_path(card, 0, with_adds, True)) / with_adds.loc[start:end, "ynicpn"]



#print(with_adds.loc[start:end, ["trci","trci_t"]])

sim = frbus.mcontrol(start, end, with_adds, targ=["trp", "trci"], traj=["trp_t", "trci_t"], inst=["trp_aerr", "trci_aerr"])
annual_sim = sim.groupby(sim.index.year).sum()

with_adds_base = frbus.init_trac(start, end, data)

with_adds_base.loc[start:end, "trp_t"] = ((calc_tpn_path(card, 0, with_adds_base, True)) / (with_adds_base.loc[start:end, "ypn"] - with_adds_base.loc[start:end, "gtn"]))
with_adds_base.loc[start:end, "trci_t"] = ( calc_tcin_path(card, 0, with_adds_base, True)) / with_adds_base.loc[start:end, "ynicpn"]


sim_base = frbus.mcontrol(start, end, with_adds_base, targ=["trp", "trci"], traj=["trp_t", "trci_t"], inst=["trp_aerr", "trci_aerr"])

annual_withadds = with_adds.groupby(with_adds.index.year).sum()
annual_baseline = sim_base.groupby(sim_base.index.year).sum()
annual_baseline = annual_baseline.loc[2017:2027]

# Making CBO and Sim dataset the same length #
annual_sim = annual_sim.loc[2017:2027]
annual_withadds = annual_withadds.loc[2017:2027]

cbo = cbo.loc[start_cbo:end_cbo]

annual_sim.index = cbo.index
annual_withadds.index = cbo.index
annual_baseline.index = cbo.index

# Calculate dynamic #
TPN_dynamic = annual_sim.loc[:, "tpn"] * (cbo.loc[:,"gdp"]/annual_withadds.loc[:, "xgdpn"])
TCIN_dynamic = annual_sim.loc[:, "tcin"] * (cbo.loc[:,"gdp"]/annual_withadds.loc[:, "xgdpn"])


TPN_baseline = annual_withadds.loc[:, "tpn"] * (cbo.loc[:,"gdp"]/annual_withadds.loc[:, "xgdpn"])
TCIN_baseline = annual_withadds.loc[:, "tcin"] * (cbo.loc[:,"gdp"]/annual_withadds.loc[:, "xgdpn"])

revenue_dynamic = TPN_dynamic + TCIN_dynamic
revenue_baseline = (annual_baseline.loc[:, "tpn"] + annual_baseline.loc[:, "tcin"])* (cbo.loc[:,"gdp"]/annual_withadds.loc[:, "xgdpn"])

delta_rev = revenue_dynamic - revenue_baseline

conventional = with_adds.loc[start:end, "tpn_d"] + with_adds.loc[start:end, "tcin_d"]
annual_conventional = conventional.groupby(conventional.index.year).sum()


print(TPN_dynamic)
print(TCIN_dynamic)
#print(delta_rev)

delta_rev.to_csv("/gpfs/gibbs/project/sarin/ser68/TCJA/Dynamic_rev_est/output/delta_rev.csv")
annual_conventional.to_csv("/gpfs/gibbs/project/sarin/ser68/TCJA/Dynamic_rev_est/output/annual_conventional.csv")

TPN_baseline.to_csv("/gpfs/gibbs/project/sarin/ser68/TCJA/Dynamic_rev_est/output/TPN_baseline.csv")
TCIN_baseline.to_csv("/gpfs/gibbs/project/sarin/ser68/TCJA/Dynamic_rev_est/output/TCIN_baseline.csv")

revenue_dynamic.to_csv("/gpfs/gibbs/project/sarin/ser68/TCJA/Dynamic_rev_est/output/dynamic_revenue.csv")


