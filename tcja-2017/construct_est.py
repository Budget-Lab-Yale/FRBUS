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

card = read_csv("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/base10_card.csv")

### STEP 1A: Disaggregate Tax Sim revenue series ###

data = build_data(card, 0)

### STEP 1B: Load FRBUS and set parameters###

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")


### STEP 2: Interpolate CBO/JCT deltas ###

cbo_delta = read_csv("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/Deltas/jct_delta.csv")

# If you want to use the delta with the foriegn income stuff added, change trci_delta to trci_delta_alt
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

data.loc[start:, 'dfpdbt'] = 0
data.loc[start:, 'dfpex'] = 1
data.loc[start:, 'dfpsrp'] = 0

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
print(type(dynamic.index))


#### STEP 4: ESTIMATE BASELINE FOR CALCULATION OF DELTA ####

# First load with_adds data for conventional scores #
data_yr = with_adds.groupby(with_adds.index.year).sum()
data_yr = data_yr.loc[start.year:end.year,]

delta = pandas.DataFrame()
dynamic_baseline = dynamic_rev(card, 0, start, end, with_adds, frbus, delta=False)    

delta["TPN_delta"] =  dynamic["TPN"] - dynamic_baseline["TPN"]
delta["TCIN_delta"] =  dynamic["TCIN"] - dynamic_baseline["TCIN"]

delta["rev_delta"] = delta["TPN_delta"] + delta["TCIN_delta"]

print(delta)
# Note that this version of delta gives a value of 0 in 2017 which is 
# what we would expect given that the jct_delta = 0 in 2017. 


#### STEP 5: Add Conventional deltas to the delta dataframe for ease ####

delta.index = data_yr.index
delta["conven_tpn"] = data_yr["tpn_d"]
delta["conven_tcin"] = data_yr["tcin_d"]
delta["conven_revenue"] = delta["conven_tpn"] + delta["conven_tcin"]


#### STEP 6: Print delta dataframe ####

delta["conven_revenue"] = delta["conven_tpn"] + delta["conven_tcin"]
delta.to_csv("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/revenue_deltas.csv")

# Print economic variables for analysis #
dynamic.to_csv("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/dynamic_econ.csv")
dynamic_baseline.to_csv("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/baseline_econ.csv")



#### STEP A-1: Checking that the backed out trax rates are correct ####
# I.E. checking that the tax rates used applied to the baseline give the conventional score #
delta.index = dynamic_baseline.index

dynamic_baseline["TPN_test"] =  dynamic["TRP_t"] * dynamic_baseline["TRP_Base"]
dynamic_baseline["TCIN_test"] =  dynamic["TRCI_t"] * dynamic_baseline["TRCI_Base"]

dynamic_baseline["TPN_base"] =  dynamic_baseline["TRP"] * dynamic_baseline["TRP_Base"]
dynamic_baseline["TCIN_base"] =  dynamic_baseline["TRCI"] * dynamic_baseline["TRCI_Base"]



delta["conven_TPN_test"] = dynamic_baseline["TPN_test"] - dynamic_baseline["TPN_base"]
delta["conven_TCIN_test"] = dynamic_baseline["TCIN_test"] - dynamic_baseline["TCIN_base"]

delta["conven_rev_test"] = delta["conven_TPN_test"] + delta["conven_TCIN_test"]
