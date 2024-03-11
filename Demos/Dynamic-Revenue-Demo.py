### Load Packages & Set time stamp ###

from pandas import DataFrame, Period, PeriodIndex, read_csv
import datetime
import pyfrbus
import sys
import os 
import numpy
import pandas
from numpy import array, shape, nan

sys.path.insert(0, "/gpfs/gibbs/project/sarin/jmk263/Repositories/FRBUS/FRBUS")

from pyfrbus.frbus import Frbus
from sim_setup import build_data, dynamic_rev
from processing import calc_delta
from punchcard import run_out, nipa_scalar

stamp = datetime.datetime.now().strftime('%Y%m%d%H')

card_path = os.path.join(os.path.dirname(__file__), "..", "punchcards", "tcja_ext_card.csv")
card = read_csv(card_path)

path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja_ext", stamp)
if not os.path.exists(path):
    os.makedirs(path)
card.to_csv(os.path.join(path, "punchcard.csv"), index=False)

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")
start = pandas.Period(card.loc[0, "start"], freq="Q")
end = pandas.Period(card.loc[0, "end"], freq="Q")

baseline = build_data(card, 0, card_dates=True)
with_adds = frbus.init_trac(start, end, baseline)

for run in range(0, len(card)):
    #### Construct and run dynamic scenario ####
    start = pandas.Period(card.loc[run, "start"], freq="Q")
    end   = pandas.Period(card.loc[run, "end"], freq="Q")

    path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja_ext", stamp, card.loc[run, "ID"])
    
    if not os.path.exists(path):
        os.makedirs(path)

    dynamic = dynamic_rev(card, run, start, end, with_adds, frbus, outpath = path)
    
    if run==0:
        dynamic_baseline = dynamic

    #### Calculate Dynamic Revenue Delta and other Output ####

    delta = calc_delta(dynamic_baseline, dynamic)
    
    #### Output delta dataframe ####

    delta.to_csv(os.path.join(path, "revenue_deltas.csv"))
    dynamic.to_csv(os.path.join(path, "dynamic_econ.csv"))
    dynamic_baseline.to_csv(os.path.join(path, "baseline_econ.csv"))
    print(f"Scenario {card.loc[run, 'ID']} completed")
