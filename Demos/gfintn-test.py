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
from pyfrbus.load_data import load_data
from sim_setup import build_data, calc_tcin_path, calc_tpn_path
from processing import calc_delta
from punchcard import run_out, nipa_scalar, read_macro, parse_tax_sim, get_housing_subsidy_rates, parse_corp_mtr
from computation import denton_boot

stamp = datetime.datetime.now().strftime('%Y%m%d%H')+"_interest_shock"

card_path = os.path.join(os.path.dirname(__file__), "..", "punchcards", "tcja_ext_foreign_interest.csv")
card = read_csv(card_path)

path = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja_ext", stamp)
if not os.path.exists(path):
    os.makedirs(path)
card.to_csv(os.path.join(path, "punchcard.csv"), index=False)

frbus_b = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model-fi-base.xml")
frbus_s = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model-fi-scen.xml")

start = pandas.Period(card.loc[0, "start"], freq="Q")
end = pandas.Period(card.loc[0, "end"], freq="Q")

baseline = build_data(card, 0, card_dates=True)
with_adds = frbus_b.init_trac(start, end, baseline)

for run in range(0, len(card)):
    #### Construct and run dynamic scenario ####
    data = with_adds

    start = pandas.Period(card.loc[run, "start"], freq="Q")
    end   = pandas.Period(card.loc[run, "end"], freq="Q")

    outpath = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja_ext", stamp, card.loc[run, "ID"])
        
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    
    macro = read_macro(card.loc[run, "macro_path"])
    macro = macro.loc[start.asfreq('Y'):end.asfreq('Y'), :]

    ts = parse_tax_sim(card, run, base=card.loc[run, "ID"]=="baseline")

    if card.loc[run, "ID"]=="baseline":
        sim = data.loc[start:end,:]
        gfintn_base = sim.loc[start:end, "gfintn"]

    else:
        per_mtr = get_housing_subsidy_rates(card, run)
        per_mtr = per_mtr.loc[:,"scen"]
        
        data.loc[start:end, "trfpm"] = per_mtr
        data.loc[start:end, "trfcim"] = parse_corp_mtr(card, run)
        data.loc[start:, "gfdrt"] = 1.1 #data.loc[start,"gfdbtn"] / data.loc[start,"xgdpn"] # Average? Max? Hardcode?

        data.loc[start:end, "yhptn_aerr"] = (data.loc[start:end, "uyhptn"] * .74 * gfintn_base)
        data.loc[start:end, "yhptn"] -= data.loc[start:end, "yhptn_aerr"]

        data.loc[start:end, "trp_t"] = (calc_tpn_path(card, run, data, True)) / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"])
        data.loc[start:end, "trci_t"] = (calc_tcin_path(card, run, data, True)) / data.loc[start:end, "ynicpn"]

        sim = frbus_s.mcontrol(start, end, data, targ=["trp", "trci"], traj=["trp_t", "trci_t"], inst=["trp_aerr", "trci_aerr"])
    
    data_yr = data.groupby(data.index.year).sum()
    sim_yr  = sim.groupby(sim.index.year).sum()
    sim_yr_avg  = sim.groupby(sim.index.year).mean() 

    macro = macro.loc[start.asfreq('Y'):end.asfreq('Y'),]
    ts = ts.loc[start.asfreq('Y'):end.asfreq('Y'),]
    data_yr = data_yr.loc[start.year:end.year,]
    sim_yr = sim_yr.loc[start.year:end.year,]
    sim_yr_avg = sim_yr_avg.loc[start.year:end.year,]
     
    macro.index = data_yr.index

    dynamic = pandas.DataFrame()
    dynamic["TPN"] =  (sim_yr["tpn"] / nipa_scalar(card, run)) * (macro["gdp"]/data_yr["xgdpn"]) 
    dynamic["TCIN"] = sim_yr["tcin"] * (macro["gdp"]/data_yr["xgdpn"])
    dynamic["total_dynamic"] = dynamic["TPN"] + dynamic["TCIN"]

    dynamic.index = pandas.PeriodIndex(dynamic.index, freq = "Y")

    dynamic["iit_rev"] = ts["iit_etr"]
    dynamic["corp_rev"] = ts["revenues_corp_tax"]
    dynamic["total_conventional"] = dynamic["iit_rev"] + dynamic["corp_rev"]

    if outpath is not None:
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        longbase = sim.filter(regex="^((?!_).)*$")
        longbase.to_csv(os.path.join(outpath,card.loc[run,"ID"]+"_LONGBASE.csv"))

    if run==0:
        dynamic_baseline = dynamic

    #### Calculate Dynamic Revenue Delta and other Output ####

    delta = calc_delta(dynamic_baseline, dynamic)
        
    #### Output delta dataframe ####

    delta.to_csv(os.path.join(outpath, "revenue_deltas.csv"))
    dynamic.to_csv(os.path.join(outpath, "dynamic_rev.csv"))
    dynamic_baseline.to_csv(os.path.join(outpath, "baseline_rev.csv"))
    print(f"Scenario {card.loc[run, 'ID']} completed")
