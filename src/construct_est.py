############### Program to construct TCJA Dyanmic Revenue Estimate ###############

### STEP 0: Load Packages & Set time stamp ###
from pandas import DataFrame, Period, PeriodIndex, read_csv
import datetime
import pyfrbus
import sys
import os
import numpy
import pandas
from typing import Union

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import build_data, denton_boot, dynamic_rev
from punchcard import get_housing_subsidy_rates

stamp = datetime.datetime.now().strftime('%Y%m%d%H')

card = read_csv("tcja_ext_card.csv")
run = 1
### STEP 1A: Disaggregate Tax Sim revenue series ###
data = build_data(card, run, raw = False, card_dates = True)

### STEP 1B: Load FRBUS and set parameters###
frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")


### STEP 2: Interpolate CBO/JCT deltas ###

# cbo_delta = read_csv("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/Deltas/jct_delta.csv")

# # If you want to use the delta with the foriegn income stuff added, change trci_delta to trci_delta_alt
# tpn_delta = (denton_boot(cbo_delta["tpn_delta"].to_numpy()))
# trci_delta = (denton_boot(cbo_delta["trci_delta"].to_numpy()))

# start = card.loc[0,"start"]
# end = card.loc[0, "end"]

# # Replace 2017 values with 0 #
# tpn_delta[0:4] = 0
# trci_delta[0:4] = 0

### STEP 3: Calculate Dynamic Revenue Estimate ###
start = pandas.Period(card.loc[run, "start"], freq="Q")
end = pandas.Period(card.loc[run, "end"], freq="Q")

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

dynamic = dynamic_rev(card, run, start, end, with_adds, frbus, delta=False)    

print(dynamic)
#### STEP 4: ESTIMATE BASELINE FOR CALCULATION OF DELTA ####

## OPTION 1: Use Build Baseline output from Josh ##
# Here just taking existing longbase file that Josh created using this program #

baseline_q = build_data(card, 0, False, True)
#load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/Baselines", str(card.loc[0, "lb_vintage"]), "LONGBASE.TXT"))

baseline_q.loc[start:, 'dfpdbt'] = 0
baseline_q.loc[start:, 'dfpex'] = 1
baseline_q.loc[start:, 'dfpsrp'] = 0

baseline_q.loc[start:, "dmpintay"] = 1
baseline_q.loc[start:, "dmptay"] = 0
baseline_q.loc[start:, "dmpalt"] = 0
baseline_q.loc[start:, "dmpex"] = 0
baseline_q.loc[start:, "dmprr"] = 0
baseline_q.loc[start:, "dmptlr"] = 0
baseline_q.loc[start:, "dmptlur"] = 0
baseline_q.loc[start:, "dmptmax"] = 0
baseline_q.loc[start:, "dmptpi"] = 0
baseline_q.loc[start:, "dmptr"] = 0
baseline_q.loc[start:, "dmptrsh"] = 0

with_adds_q = frbus.init_trac(start, end, baseline_q)

## Make annual ##
#### STEP 4: ESTIMATE BASELINE FOR CALCULATION OF DELTA ####

# First load with_adds data for conventional scores #
data_yr = with_adds.groupby(with_adds.index.year).sum()
data_yr = data_yr.loc[start.year:end.year,]

delta = pandas.DataFrame()
dynamic_baseline = dynamic_rev(card, 0, start, end, with_adds_q, frbus, delta=False)    

delta["TPN_delta"] =  dynamic["TPN"] - dynamic_baseline["TPN"]
delta["TCIN_delta"] =  dynamic["TCIN"] - dynamic_baseline["TCIN"]

delta["rev_delta"] = delta["TPN_delta"] + delta["TCIN_delta"]

print(delta)

#### STEP 5: Add Conventional deltas to the delta dataframe for ease ####

#### STEP 6: Print delta dataframe ####

path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja_ext", card.loc[run, "ID"])
if not os.path.exists(path):
    os.makedirs(path)

delta.to_csv(os.path.join(path, "revenue_deltas.csv"))
# Print economic variables for analysis #
dynamic.to_csv(os.path.join(path, "dynamic_econ.csv"))
dynamic_baseline.to_csv(os.path.join(path, "baseline_econ.csv"))

