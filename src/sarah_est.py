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

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import build_data, denton_boot, dynamic_rev

from punchcard import parse_tax_sim, read_gdp, parse_corp_sim


#can move into loop if we want a vintage stamp for every model run
ct = datetime.datetime.now()
stamp = str(ct.year)+str(ct.month)+str(ct.day)+str(ct.hour)

card = read_csv("/gpfs/gibbs/project/sarin/ser68/TCJA/Dynamic_rev_est/base10_card.csv")

### STEP 1A: Disaggregate Tax Sim revenue series ###

data = build_data(card, 0)

### STEP 1B: Load FRBUS and set parameters###

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")


### STEP 2: Interpolate CBO/JCT deltas ###

cbo_delta = read_csv("/gpfs/gibbs/project/sarin/ser68/TCJA/Dynamic_rev_est/Deltas/cbo_delta.csv")

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

dynamic = dynamic_rev(card, 0, start, end, with_adds, frbus, delta=True)    

print(dynamic)
