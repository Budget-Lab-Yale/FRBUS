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

stamp = datetime.datetime.now().strftime('%Y%m%d%H')+"_rstar"

card_path = os.path.join(os.path.dirname(__file__), "..", "punchcards", "tcja_ext_rstar_test.csv")
card = read_csv(card_path)

path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja_ext", stamp)
if not os.path.exists(path):
    os.makedirs(path)
card.to_csv(os.path.join(path, "punchcard.csv"), index=False)

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")

ver = ["dmpintay+10star", "dmpalt+nostar", "dmpalt+rstar", "dmpalt+10star"]

for test in range(0,4):
    print(f"Testing version: {ver[test]}")
    dex = 4 * test
    start = pandas.Period(card.loc[dex, "start"], freq="Q")
    end = pandas.Period(card.loc[dex, "end"], freq="Q")

    baseline = build_data(card, dex, card_dates=True)
    with_adds = frbus.init_trac(start, end, baseline)

    for run in range(dex, dex+4):
        #### Construct and run dynamic scenario ####
        start = pandas.Period(card.loc[run, "start"], freq="Q")
        end   = pandas.Period(card.loc[run, "end"], freq="Q")

        outpath = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja_ext", stamp, card.loc[run, "ID"] + "-" + ver[test])
        
        if not os.path.exists(outpath):
            os.makedirs(outpath)

        dynamic = dynamic_rev(card, run, start, end, with_adds, frbus, outpath = outpath)
        
        if (run % 4)==0:
            dynamic_baseline = dynamic

        #### Calculate Dynamic Revenue Delta and other Output ####

        delta = calc_delta(dynamic_baseline, dynamic)
        
        #### Output delta dataframe ####

        delta.to_csv(os.path.join(outpath, "revenue_deltas.csv"))
        dynamic.to_csv(os.path.join(outpath, "dynamic_rev.csv"))
        dynamic_baseline.to_csv(os.path.join(outpath, "baseline_rev.csv"))
        print(f"Scenario {card.loc[run, 'ID']} completed")

