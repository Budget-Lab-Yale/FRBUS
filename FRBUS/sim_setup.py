import pandas
import scipy
import os

from pandas import DataFrame, Period, PeriodIndex, read_csv
from numpy import array, NaN
from typing import Union
from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from punchcard import parse_tax_sim, read_macro, parse_corp_mtr, get_housing_subsidy_rates, nipa_scalar
from computation import denton_boot

def levers(data: DataFrame, card: DataFrame, run: int):
    #---------------------------------------------------------------------
    # Sets fiscal and monetary policy levers for all simulations.
    # Parameters:
    #   data (DataFrame): Raw longbase file from FOMC
    #   dfp  (str)      : Active fiscal policy setting (Debt targetting, surplus targetting, or exogenous)
    #   dmp  (str)      : Active monetary policy setting (Typically inertial Taylor rule)
    # Returns:
    #   data (DataFrame): Longbase with set levers
    #---------------------------------------------------------------------
    start = pandas.Period(card.loc[run, "start"], freq="Q")
    end = pandas.Period(card.loc[run, "end"], freq="Q")
    dfp = card.loc[run, "dfp"]
    dmp = card.loc[run, "dmp"]
    rstar = card.loc[run, "rstar"]
    
    fiscal = [col for col in data.columns if 'dfp' in col]
    fiscal.remove(dfp)
    monetary = [col for col in data.columns if 'dmp' in col]
    monetary.remove(dmp)

    data.loc[:, [dfp, dmp]] = 1
    data.loc[:, fiscal + monetary] = 0
    
    if(rstar=="on"):
        data.loc[:, "drstar"] = 1
    elif(rstar=="delay"):
        data.loc[start:start+39, "drstar"] = 0
        data.loc[start+40:end, "drstar"] = 1
    else:
        data.loc[:, "drstar"] = 0

    return(data)

def build_data(card: DataFrame, run: int, card_dates = False):
    #---------------------------------------------------------------------
    # This function constructs a baseline dataset using the mcontrol protocol
    # against which alternate scenario runs are compared. 
    # Parameters:
    #   card   (DataFrame): Punchcard of scenario specific parameters
    #   run          (int): Row for the card dataframe.
    #   card_dates  (bool): Flag for if the baseline is constructed by YBL or the FOMC
    # Returns:
    #   longbase (DataFrame): FRB longbase.txt file adjusted to suit this 
    #                         specific policy test.
    #---------------------------------------------------------------------
    longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))
    
    # Get tax variable paths from Tax Simulator
    ts = parse_tax_sim(card, run, True)

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
    per_mtr = get_housing_subsidy_rates(card, run)
    per_mtr = per_mtr.loc[:,"base"]
    
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
    TPN_fs = denton_boot(macro["TPN_ts"].to_numpy())
    TCIN_fs = denton_boot(macro["TCIN_cs"].to_numpy())
    gfsrpn_dent = denton_boot(macro["gfsrpn_macro"].to_numpy())
    
    # Set up fiscal/monetary policy levers
    frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model-abroad-base.xml", mce="mcap+wp")

    longbase = levers(longbase, card, run)

    # Set paths and solve
    with_adds = frbus.init_trac(start, end, longbase)
    
    with_adds.loc[start:end, "tpn_t"] = TPN_fs * nipa_scalar(card, run)
    with_adds.loc[start:end, "tcin_t"] = TCIN_fs
    with_adds.loc[start:end, "trfpm"] = per_mtr
    with_adds.loc[start:end, "trfcim"] = parse_corp_mtr(card, run)
    with_adds.loc[start:, "gfdrt"] = 1.1 #with_adds.loc[start,"gfdbtn"] / with_adds.loc[start,"xgdpn"] # Average? Max? Hardcode?
    with_adds.loc[start:end, "gfsrpn_t"] = gfsrpn_dent

    with_adds.loc[start:end, "xgdpn_t"] = with_adds.loc[start:end, "xgdpn"]
    with_adds.loc[start:end, "xgdp_t"] = with_adds.loc[start:end, "xgdp"]
    with_adds.loc[start:end, "picxfe_t"] = with_adds.loc[start:end, "picxfe"]
    with_adds.loc[start:end, "lur_t"] = with_adds.loc[start:end, "lur"]
    with_adds.loc[start:end, "rff_t"] = with_adds.loc[start:end, "rff"]

    sim = frbus.mcontrol(start, end, with_adds, 
        targ=["tpn",      "tcin",      "xgdpn",      "gfsrpn",      "xgdp",      "picxfe",      "lur",      "rff"], 
        traj=["tpn_t",    "tcin_t",    "xgdpn_t",    "gfsrpn_t",    "xgdp_t",    "picxfe_t",    "lur_t",    "rff_t"], 
        inst=["trp_aerr", "trci_aerr", "xgdpn_aerr", "gfsrpn_aerr", "xgdp_aerr", "picxfe_aerr", "lur_aerr", "rff_aerr"])
    
    # Filter out values not found in original longbase (they all contain '_')
    out = sim.filter(regex="^((?!_).)*$")

    # Replace section of original longbase within our timeframe with new values
    #longbase.loc[start:end,:] = out.loc[start:end,:]

    #return(longbase)
    return(out)

def calc_tpn_path(card: DataFrame, run: int, data: DataFrame, card_dates = False):
    #---------------------------------------------------------------------
    # Calculates Personal Income Tax Revenue path based on Tax Simulator output
    # Parameters:
    #   card     (DataFrame): Punchcard of scenario specific parameters
    #   run            (int): Row for the card dataframe.
    #   data     (DataFrame): Processed dataset pre-scenario simulation
    #   card_dates    (bool): (optional) Flag to derive scenario start and end dates from the card
    # Returns:
    #   TPN_fs (Vector[int]): Quarterly Personal Income Tax Revenue in FRBUS dollars
    #---------------------------------------------------------------------    
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
    TPN_fs *= nipa_scalar(card, run)
    
    return(TPN_fs) 

def calc_tcin_path(card: DataFrame, run: int, data: DataFrame, card_dates = False):
    #---------------------------------------------------------------------
    # Calculates Corporate Income Tax Revenue path based on Tax Simulator output
    # Parameters:
    #   card     (DataFrame): Punchcard of scenario specific parameters
    #   run            (int): Row for the card dataframe.
    #   data     (DataFrame): Processed dataset pre-scenario simulation
    #   card_dates    (bool): (optional) Flag to derive scenario start and end dates from the card
    # Returns:
    #   TPN_fs (Vector[int]): Quarterly Corporate Income Tax Revenue in FRBUS dollars
    #---------------------------------------------------------------------    
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
    #---------------------------------------------------------------------
    # Calculates Personal Income Tax Revenue path based on Tax Simulator output
    # Parameters:
    #   card     (DataFrame): Punchcard of scenario specific parameters
    #   run            (int): Row for the card dataframe.
    #   start       (Period): Beginning date of scenario
    #   end         (Period): End date of scenario
    #   data     (DataFrame): Processed dataset pre-scenario simulation
    #   frbus        (Frbus): Frbus model object
    #   outpath       (path): (optional) Filepath for adjusted longbase output
    #   delta         (bool): (optional) Flag for if dynamic revenue path includes an off model delta
    # Returns:
    #   dynamic  (DataFrame): Dynamic revenue score of scenario. Includes conventional score.
    #---------------------------------------------------------------------    
    macro = read_macro(card.loc[run, "macro_path"])
    macro = macro.loc[start.asfreq('Y'):end.asfreq('Y'), :]

    ts = parse_tax_sim(card, run, base=card.loc[run, "ID"]=="baseline")

    per_mtr = get_housing_subsidy_rates(card, run)
    per_mtr = per_mtr.loc[:,"scen"]

    if delta:
        data.loc[start:end, "trp_t"] = ((data.loc[start:end, "tpn_d"] + calc_tpn_path(card, run, data, True)) / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"]))
        data.loc[start:end, "trci_t"] = (data.loc[start:end, "tcin_d"] + calc_tcin_path(card, run, data, True)) / data.loc[start:end, "ynicpn"]
    
    else:
        data.loc[start:end, "trp_t"] = (calc_tpn_path(card, run, data, True)) / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"])
        data.loc[start:end, "trci_t"] = (calc_tcin_path(card, run, data, True)) / data.loc[start:end, "ynicpn"]
    
    data.loc[start:end, "trfpm"] = per_mtr
    data.loc[start:end, "trfcim"] = parse_corp_mtr(card, run)
    data.loc[start:, "gfdrt"] = 1.1 #data.loc[start,"gfdbtn"] / data.loc[start,"xgdpn"] # Average? Max? Hardcode?
    
    if card.loc[run, "ID"]=="baseline":
        macro['gfsrpn_macro'] = (macro["rev"] - macro["outlays"]) / macro["gdp"]
        temp = data.loc[start:end, "xgdpn"]
        temp = temp.groupby(temp.index.year).sum()
        macro['gfsrpn_macro'] *= temp
        gfsrpn_dent = denton_boot(macro['gfsrpn_macro'].to_numpy())

        data.loc[start:end, "xgdpn_t"]  = data.loc[start:end, "xgdpn"]
        data.loc[start:end, "xgdp_t"]   = data.loc[start:end, "xgdp"]
        data.loc[start:end, "picxfe_t"] = data.loc[start:end, "picxfe"]
        data.loc[start:end, "lur_t"]    = data.loc[start:end, "lur"]
        data.loc[start:end, "rff_t"]    = data.loc[start:end, "rff"]
        data.loc[start:end, "gfsrpn_t"] = gfsrpn_dent
        
        sim = frbus.mcontrol(start, end, data, 
            targ=["trp",      "trci",      "xgdpn",      "gfsrpn",      "xgdp",      "picxfe",      "lur",      "rff"], 
            traj=["trp_t",    "trci_t",    "xgdpn_t",    "gfsrpn_t",    "xgdp_t",    "picxfe_t",    "lur_t",    "rff_t"], 
            inst=["trp_aerr", "trci_aerr", "xgdpn_aerr", "gfsrpn_aerr", "xgdp_aerr", "picxfe_aerr", "lur_aerr", "rff_aerr"])

    else:
        sim = frbus.mcontrol(start, end, data, targ=["trp", "trci"], traj=["trp_t", "trci_t"], inst=["trp_aerr", "trci_aerr"])
    
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

        out = sim.filter(regex="^((?!_).)*$")
        
        longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))
        longbase.loc[start:end,:] = out.loc[start:end,:]
        longbase.to_csv(os.path.join(outpath,card.loc[run,"ID"]+"_LONGBASE.csv"))

    return(dynamic)

