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

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import levers, build_data, denton_boot, dynamic_rev

stamp = datetime.datetime.now().strftime('%Y%m%d%H')

path = os.path.realpath(__file__)
dir = os.path.dirname(path)
dir = dir.replace('src', 'punchcards')
os.chdir(dir)
card = read_csv("tcja_ext_card.csv")

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")
start = pandas.Period(card.loc[0, "start"], freq="Q")
end = pandas.Period(card.loc[0, "end"], freq="Q")

baseline = build_data(card, 0, card_dates=True)
baseline = levers(start, end, baseline)
with_adds_b = frbus.init_trac(start, end, baseline)
dynamic_baseline = dynamic_rev(card, 0, start, end, with_adds_b, frbus)

for run in range(0, len(card)):
    #### Construct and run dynamic scenario ####
    start = pandas.Period(card.loc[run, "start"], freq="Q")
    end = pandas.Period(card.loc[run, "end"], freq="Q")

    data = build_data(card, run, card_dates=True)
    data = levers(start, end, data)
    with_adds_b = frbus.init_trac(start, end, data)
    dynamic = dynamic_rev(card, run, start, end, with_adds_b, frbus)

    #### Calculate Dynamic Revenue Delta ####

    delta = pandas.DataFrame()  

    delta["TPN_delta"] =  dynamic["TPN"] - dynamic_baseline["TPN"]
    delta["TCIN_delta"] =  dynamic["TCIN"] - dynamic_baseline["TCIN"]

    delta["rev_delta"] = delta["TPN_delta"] + delta["TCIN_delta"]

    print(delta)

    #### Output delta dataframe ####

    path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja_ext",stamp, card.loc[run, "ID"])
    if not os.path.exists(path):
        os.makedirs(path)

    delta.to_csv(os.path.join(path, "revenue_deltas.csv"))
    dynamic.to_csv(os.path.join(path, "dynamic_econ.csv"))
    dynamic_baseline.to_csv(os.path.join(path, "baseline_econ.csv"))