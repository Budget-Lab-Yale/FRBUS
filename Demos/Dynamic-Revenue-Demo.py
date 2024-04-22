### Load Packages & Set time stamp ###

from pandas import DataFrame, Period, PeriodIndex, read_csv
import datetime
import pyfrbus
import sys
import os 
import numpy
import pandas
from numpy import array, shape, nan

sys.path.insert(0, "/gpfs/gibbs/project/sarin/jmk263/Repositories/FRBUS/src")

from pyfrbus.frbus import Frbus
from sim_setup import build_data, dynamic_rev
from processing import calc_delta, process_dynamic_rev_delta
from punchcard import nipa_scalar

stamp = datetime.datetime.now().strftime('%Y%m%d%H%M')
print(stamp)

# Reading in topline parameters for the set of scenrios #
card_path = os.path.join(os.path.dirname(__file__), "..", "punchcards", "ctc_card.csv")
card = read_csv(card_path)

# Creating output directory #
path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/ctc", stamp)
if not os.path.exists(path):
    os.makedirs(path)
card.to_csv(os.path.join(path, "punchcard.csv"), index=False)

# Loading in multiple versions of FRBUS equations for baseline/scenarios #
frbus_b = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model-fi-base.xml")
frbus_s = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model-fi-scen.xml")

start = pandas.Period(card.loc[0, "start"], freq="Q")
end = pandas.Period(card.loc[0, "end"], freq="Q")

# Creates baseline values for 
baseline = build_data(card, 0, card_dates=True, frbus=frbus_b)
with_adds = frbus_b.init_trac(start, end, baseline)

for run in range(0, len(card)):
    #### Construct and run dynamic scenario ####
    start = pandas.Period(card.loc[run, "start"], freq="Q")
    end   = pandas.Period(card.loc[run, "end"], freq="Q")

    outpath = os.path.join(path, card.loc[run, "ID"])
    
    if not os.path.exists(outpath):
        os.makedirs(outpath)

    dynamic, newbase = dynamic_rev(card, run, start, end, with_adds, frbus_s, outpath = outpath)
    
    if run==0:
        dynamic_baseline = dynamic
    
    else:
        process_dynamic_rev_delta(card, run, stamp, outpath)

    #### Calculate Dynamic Revenue Delta and other Output ####

    delta = calc_delta(dynamic_baseline, dynamic)
    
    #### Output delta dataframe ####

    delta.to_csv(os.path.join(outpath, "revenue_deltas.csv"))
    dynamic.to_csv(os.path.join(outpath, "dynamic_econ.csv"))
    dynamic_baseline.to_csv(os.path.join(outpath, "baseline_econ.csv"))

    print(f"Scenario {card.loc[run, 'ID']} completed")
    