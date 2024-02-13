import pandas
import scipy
import os

from pandas import DataFrame, Period, PeriodIndex, read_csv
from numpy import array
from typing import Union
from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from punchcard import parse_tax_sim, read_macro, parse_corp_mtr, get_housing_subsidy_rates
from computation import denton_boot

def levers(data: DataFrame, dfp: str, dmp: str):
    fiscal = [col for col in data.columns if 'dfp' in col]
    fiscal.remove(dfp)
    monetary = [col for col in data.columns if 'dmp' in col]
    monetary.remove(dmp)

    data.loc[:, [dfp, dmp]] = 1
    data.loc[:, fiscal + monetary] = 0
        
    return(data)

def build_data(card: DataFrame, run: int, base = False, card_dates = False, dynamic = False):
    #---------------------------------------------------------------------
    # This function constructs a baseline dataset using the mcontrol protocol
    # against which alternate scenario runs are compared. 
    # Parameters:
    #   card (DataFrame): Punchcard of test specific parameters
    #   run  (int)      : Row for the card dataframe.
    #   raw  (bool)     : Flag for if the baseline is constructed by YBL or the FOMC
    # Returns:
    #   longbase (DataFrame): FRB longbase.txt file adjusted to suit this 
    #                         specific policy test.
    #---------------------------------------------------------------------
    longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))
    
    # Get tax variable paths from Tax Simulator
    ts = parse_tax_sim(card, run, base)

    if card_dates:
        start = pandas.Period(card.loc[run, "start"][0:4], freq="Y")
        end = pandas.Period(card.loc[run, "end"][0:4], freq="Y")
    else:
        start = ts.index[0]
        end = ts.index[len(ts)-1]

    # Restrict to dates under consideration
    ts = ts.loc[start:end,:]

    # Read in macro economic forecast, combine with variable paths and convert to % of GDP
    macro = read_macro(card.loc[run, "macro_path"])
    macro = macro.loc[start:end,:]
    macro['TPN_ts'] = ts["iit_etr"] / macro["gdp"]
    macro['TCIN_cs'] = ts["revenues_corp_tax"] / macro["gdp"]
    macro['gfsrpn_macro'] = (macro["rev"] - macro["outlays"]) / macro["gdp"]

    # Calculate / Parse MTRs
    corp_mtr = parse_corp_mtr(card, run)
    corp_mtr = corp_mtr.loc[start:end,:]
    per_mtr = get_housing_subsidy_rates(card, run)
    per_mtr = per_mtr.loc[start:end,:]
    
    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    # Convert variables to "FRBUS $"
    temp = longbase.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = macro.index
    macro["TPN_ts"] *= temp
    macro["TCIN_cs"] *= temp 
    macro["gfsrpn_macro"] *= temp

    # Interpolate annual values to quarterly
    # TRFPM is resigned to reflect FRBUS's interpretation of the value as a subsidy
    TPN_fs = denton_boot(macro["TPN_ts"].to_numpy())
    TCIN_fs = denton_boot(macro["TCIN_cs"].to_numpy())
    TRFPM_fs = (denton_boot(per_mtr["base"].to_numpy())) * -400 # -1 * 4 * 100
    gfsrpn_dent = denton_boot(macro["gfsrpn_macro"].to_numpy())
    TRFCIM_fs = (denton_boot(corp_mtr["corp.rate"].to_numpy())) * 4
    
    # Set up fiscal/monetary policy levers
    frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")

    longbase = levers(longbase, card.loc[run, "dfp"], card.loc[run, "dmp"])

    # Set paths and solve
    with_adds = frbus.init_trac(start, end, longbase)
    with_adds.loc[start:end, "tpn_t"] = TPN_fs * 1.25
    with_adds.loc[start:end, "tcin_t"] = TCIN_fs
    with_adds.loc[start:end, "trfpm"] = TRFPM_fs
    with_adds.loc[start:end, "trfcim"] = TRFCIM_fs
    with_adds.loc[start:, "gfdrt"] = 1.1 #with_adds.loc[start,"gfdbtn"] / with_adds.loc[start,"xgdpn"] # Average? Max? Hardcode?
    with_adds.loc[start:end, "gfsrpn_t"] = gfsrpn_dent

    with_adds.loc[start:end, "xgdpn_t"] = with_adds.loc[start:end, "xgdpn"]
    with_adds.loc[start:end, "xgdp_t"] = with_adds.loc[start:end, "xgdp"]
    with_adds.loc[start:end, "picxfe_t"] = with_adds.loc[start:end, "picxfe"]
    with_adds.loc[start:end, "lur_t"] = with_adds.loc[start:end, "lur"]
    with_adds.loc[start:end, "rff_t"] = with_adds.loc[start:end, "rff"]

    sim = frbus.mcontrol(start, end, with_adds, 
        targ=["tpn",      "tcin",      "xgdpn",    "gfsrpn",      "xgdp",     "picxfe",      "lur",      "rff"], 
        traj=["tpn_t",    "tcin_t",    "xgdpn_t",  "gfsrpn_t",    "xgdp_t",   "picxfe_t",    "lur_t",    "rff_t"], 
        inst=["trp_aerr", "trci_aerr", "xpn_aerr", "ugfsrp_aerr", "xgdp_aerr", "picxfe_aerr", "lur_aerr", "rff_aerr"])
    
    # Filter out values not found in original longbase (they all contain '_')
    out = sim.filter(regex="^((?!_).)*$")

    # Replace section of original longbase within our timeframe with new values
    longbase.loc[start:end,:] = out.loc[start:end,:]

    if dynamic:
        data_yr = with_adds.loc[start:end,:]
        data_yr = data_yr.groupby(data_yr.index.year).sum()
        sim = sim.loc[start:end,:]
        sim_yr  = sim.groupby(sim.index.year).sum() 

        macro.index = data_yr.index

        dynamic = pandas.DataFrame()
        dynamic["TPN"] =  (sim_yr["tpn"] / 1.25) * (macro["gdp"]/data_yr["xgdpn"])
        dynamic["TCIN"] = sim_yr["tcin"] * (macro["gdp"]/data_yr["xgdpn"])
        dynamic["total_dynamic"] = dynamic["TPN"] + dynamic["TCIN"]

        dynamic.index = ts.index

        dynamic["iit_rev"] = ts["iit_etr"]
        dynamic["corp_rev"] = ts["revenues_corp_tax"]
        dynamic["total_conventional"] = dynamic["iit_rev"] + dynamic["corp_rev"]

        return(longbase, dynamic)
    
    else:
        return(longbase)

def calc_tpn_path(card: DataFrame, run: int, data: DataFrame, card_dates = False):
    
    ts = parse_tax_sim(card, run, card.loc[run, "ID"]=="baseline")
    
    if card_dates:
        start = pandas.Period(card.loc[run, "start"][0:4], freq="Y")
        end = pandas.Period(card.loc[run, "end"][0:4], freq="Y")
    else:
        start = ts.index[0]
        end = ts.index[len(ts)-1]

    macro = read_macro(card.loc[run, "macro_path"])
    macro = macro.loc[start:end]
    macro['TPN_ts'] = ts["iit_etr"] / macro["gdp"]
    
    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    temp = data.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = macro.index
    macro["TPN_ts"] *= temp

    TPN_fs = (denton_boot(macro["TPN_ts"].to_numpy()))
    
    return(TPN_fs)

def calc_tcin_path(card: DataFrame, run: int, data: DataFrame, card_dates = False):
    if(card.loc[run, "ID"]=="baseline"):
        ts = parse_tax_sim(card, run, True)
    else:
        ts = parse_tax_sim(card, run, False)

    if card_dates:
        start = pandas.Period(card.loc[run, "start"][0:4], freq="Y")
        end = pandas.Period(card.loc[run, "end"][0:4], freq="Y")
    else:
        start = ts.index[0]
        end = ts.index[len(ts)-1]

    macro = read_macro(card.loc[run, "macro_path"])
    macro = macro.loc[start:end]
    ts = ts.loc[start:end]
    macro['TCIN_cs'] = ts["revenues_corp_tax"] / macro["gdp"]

    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    temp = data.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = macro.index
    macro["TCIN_cs"] *= temp

    TCIN_fs = (denton_boot(macro["TCIN_cs"].to_numpy()))
    
    return(TCIN_fs)

def dynamic_rev(card: DataFrame, run: int, start: Period, end: Period, data: DataFrame, frbus: Frbus, outpath = None, delta=False):
    macro = read_macro(card.loc[run, "macro_path"])
    macro = macro.loc[start.asfreq('Y'):end.asfreq('Y'), :]

    ts = parse_tax_sim(card, run, base=card.loc[run, "ID"]=="baseline")

    per_mtr = get_housing_subsidy_rates(card, run)
    per_mtr = per_mtr.loc[start.asfreq('Y'):end.asfreq('Y'),:]
    corp_mtr = parse_corp_mtr(card, run)
    corp_mtr = corp_mtr.loc[start.asfreq('Y'):end.asfreq('Y'),:]

    if delta:
        data.loc[start:end, "trp_t"] = ((data.loc[start:end, "tpn_d"] + calc_tpn_path(card, run, data, True)) / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"]))
        data.loc[start:end, "trci_t"] = (data.loc[start:end, "tcin_d"] + calc_tcin_path(card, run, data, True)) / data.loc[start:end, "ynicpn"]
    
    else:
        data.loc[start:end, "trp_t"] = (calc_tpn_path(card, run, data, True)) / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"])
        data.loc[start:end, "trci_t"] = (calc_tcin_path(card, run, data, True)) / data.loc[start:end, "ynicpn"]
    

    data.loc[start:end, "trfpm"] = (denton_boot(per_mtr["scen"].to_numpy())) * -400
    data.loc[start:end, "trfcim"] = (denton_boot(corp_mtr["corp.rate"].to_numpy())) * 4
    data.loc[start:, "gfdrt"] = 1.1 #data.loc[start,"gfdbtn"] / data.loc[start,"xgdpn"] # Average? Max? Hardcode?
    
    # if card.loc[run, "ID"]=="baseline":
    #     macro['gfsrpn_macro'] = (macro["rev"] - macro["outlays"]) / macro["gdp"]
    #     macro['gfsrpn_macro'] *= data.loc[start:end, "xgdpn"].groupby(data.index.year).sum()
    #     gfsrpn_dent = denton_boot(macro['gfsrpn_macro'].to_numpy())

    #     data.loc[start:end, "xgdpn_t"]  = data.loc[start:end, "xgdpn"]
    #     data.loc[start:end, "xgdp_t"]   = data.loc[start:end, "xgdp"]
    #     data.loc[start:end, "picxfe_t"] = data.loc[start:end, "picxfe"]
    #     data.loc[start:end, "lur_t"]    = data.loc[start:end, "lur"]
    #     data.loc[start:end, "rff_t"]    = data.loc[start:end, "rff"]
    #     data.loc[start:end, "gfsrpn_t"] = gfsrpn_dent
        
    #     sim = frbus.mcontrol(start, end, data, 
    #         targ=["trp",      "trci",      "xgdpn",    "gfsrpn",      "xgdp",     "picxfe",      "lur",      "rff"], 
    #         traj=["trp_t",    "trci_t",    "xgdpn_t",  "gfsrpn_t",    "xgdp_t",   "picxfe_t",    "lur_t",    "rff_t"], 
    #         inst=["trp_aerr", "trci_aerr", "xpn_aerr", "ugfsrp_aerr", "xgdp_aerr", "picxfe_aerr", "lur_aerr", "rff_aerr"])

    # else:
    sim = frbus.mcontrol(start, end, data, targ=["trp", "trci"], traj=["trp_t", "trci_t"], inst=["trp_aerr", "trci_aerr"])
    
    sim.loc[start:end, "tpn"] /= 1.25

    data_yr = data.groupby(data.index.year).sum()
    sim_yr  = sim.groupby(sim.index.year).sum()
    sim_yr_avg  = sim.groupby(sim.index.year).mean() #for variables not converted between macro/FRBUS $

    macro = macro.loc[start.asfreq('Y'):end.asfreq('Y'),]
    ts = ts.loc[start.asfreq('Y'):end.asfreq('Y'),]
    data_yr = data_yr.loc[start.year:end.year,]
    sim_yr = sim_yr.loc[start.year:end.year,]
    sim_yr_avg = sim_yr_avg.loc[start.year:end.year,]
    
    macro.index = data_yr.index

    dynamic = pandas.DataFrame()
    dynamic["TPN"] =  sim_yr["tpn"] * (macro["gdp"]/data_yr["xgdpn"])
    dynamic["TCIN"] = sim_yr["tcin"] * (macro["gdp"]/data_yr["xgdpn"])
    dynamic["total_dynamic"] = dynamic["TPN"] + dynamic["TCIN"]

    dynamic.index = pandas.PeriodIndex(dynamic.index, freq = "Y")

    dynamic["iit_rev"] = ts["iit_etr"]
    dynamic["corp_rev"] = ts["revenues_corp_tax"]
    dynamic["total_conventional"] = dynamic["iit_rev"] + dynamic["corp_rev"]

    if outpath is not None:
        out = sim.filter(regex="^((?!_).)*$")
        
        longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))
        longbase.loc[start:end,:] = out.loc[start:end,:]
        longbase.to_csv(os.path.join(outpath,card.loc[run,"ID"]+"_LONGBASE.csv"))

    return(dynamic)

