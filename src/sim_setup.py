import pandas
import numpy as np
import scipy
import os

from pandas import DataFrame, Period, PeriodIndex, read_csv
from numpy import array
from typing import Union
from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from punchcard import parse_tax_sim, read_macro, parse_corp_mtr, get_housing_subsidy_rates

def levers(start: Union[str, Period], end: Union[str, Period], data: DataFrame, dfp: str, dmp: str):
    fiscal = [col for col in data.columns if 'dfp' in col]
    fiscal.remove(dfp)
    monetary = [col for col in data.columns if 'dmp' in col]
    monetary.remove(dmp)

    data.loc[start:end, [dfp, dmp]] = 1
    for i in fiscal:
        data.loc[start:end, i] = 0
    for j in monetary:
        data.loc[start:end, j] = 0
        
    return(data)

def build_data(card: DataFrame, run: int, raw = False, card_dates = False):
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
    if raw:
        longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))
    else:
        longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/Baselines", str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))

    # Get tax variable paths from Tax Simulator
    ts = parse_tax_sim(card, run, base = True)

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

    # Interpolate annual values to quarterly
    # TRFPM is resigned to reflect FRBUS's interpretation of the value as a subsidy
    TPN_fs = denton_boot(macro["TPN_ts"].to_numpy())
    TCIN_fs = denton_boot(macro["TCIN_cs"].to_numpy())
    TRFPM_fs = (denton_boot(per_mtr["base"].to_numpy())) * -4
    TRFCIM_fs = (denton_boot(corp_mtr["corp.rate"].to_numpy())) * 4

    # Set up fiscal/monetary policy levers
    frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")
    longbase.loc[start:end, "dfpsrp"] = 0
    longbase.loc[start:end, "dfpdbt"] = 1
    longbase.loc[start:end, "dfpex"] = 0

    longbase.loc[start:, "dmpintay"] = 1
    longbase.loc[start:, "dmptay"] = 0
    longbase.loc[start:, "dmpalt"] = 0
    longbase.loc[start:, "dmpex"] = 0
    longbase.loc[start:, "dmprr"] = 0
    longbase.loc[start:, "dmptlr"] = 0
    longbase.loc[start:, "dmptlur"] = 0
    longbase.loc[start:, "dmptmax"] = 0
    longbase.loc[start:, "dmptpi"] = 0
    longbase.loc[start:, "dmptr"] = 0
    longbase.loc[start:, "dmptrsh"] = 0

    # Set paths and solve
    with_adds = frbus.init_trac(start, end, longbase)
    with_adds.loc[start:end, "tpn_t"] = TPN_fs 
    with_adds.loc[start:end, "tcin_t"] = TCIN_fs
    with_adds.loc[start:end, "trfpm"] = TRFPM_fs
    with_adds.loc[start:end, "trfcim"] = TRFCIM_fs

    out = frbus.mcontrol(start, end, with_adds, targ=["tpn", "tcin"], traj=["tpn_t", "tcin_t"], inst=["trp_aerr", "trci_aerr"])

    # Filter out values not found in original longbase (they all contain '_')
    out = out.filter(regex="^((?!_).)*$")

    # Replace section of original longbase within our timeframe with new values
    longbase.loc[start:end,:] = out.loc[start:end,:]
    return(longbase)

def calc_tpn_path(card: DataFrame, run: int, data: DataFrame, card_dates = False):
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

def dynamic_rev(card: DataFrame, run: int, start: Period, end: Period, data: DataFrame, frbus: Frbus, delta=False):
    macro = read_macro(card.loc[run, "macro_path"])

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
    
    data.loc[start:end, "trfpm"] = (denton_boot(per_mtr["scen"].to_numpy())) * -4
    data.loc[start:end, "trfcim"] = (denton_boot(corp_mtr["corp.rate"].to_numpy())) * 4

    sim = frbus.mcontrol(start, end, data, targ=["trp", "trci"], traj=["trp_t", "trci_t"], inst=["trp_aerr", "trci_aerr"])

    data_yr = data.groupby(data.index.year).sum()
    sim_yr  = sim.groupby(sim.index.year).sum()
    sim_yr_avg  = sim.groupby(sim.index.year).mean() #for variables not converted between macro/FRBUS $

    macro = macro.loc[start.asfreq('Y'):end.asfreq('Y'),]
    data_yr = data_yr.loc[start.year:end.year,]
    sim_yr = sim_yr.loc[start.year:end.year,]
    sim_yr_avg = sim_yr_avg.loc[start.year:end.year,]
    
    macro.index = data_yr.index

    dynamic = pandas.DataFrame()
    dynamic["TPN"] =  sim_yr["tpn"] * (macro["gdp"]/data_yr["xgdpn"])
    dynamic["TCIN"] = sim_yr["tcin"] * (macro["gdp"]/data_yr["xgdpn"])

    ### Adding other variables of interest for output ####

    # Real GDP and its components #
    dynamic["XGDP"] = sim_yr["xgdp"] * (macro["gdp"]/data_yr["xgdpn"]) # Real GDP
    dynamic["ECNIA"] = sim_yr["ecnia"] * (macro["gdp"]/data_yr["xgdpn"]) # PCE
    dynamic["EBFI"] = sim_yr["ebfi"] * (macro["gdp"]/data_yr["xgdpn"]) # Bus Fixed Investment
    dynamic["EH"] = sim_yr["eh"] * (macro["gdp"]/data_yr["xgdpn"]) # Residential investment
    dynamic["EGFE"] = sim_yr["egfe"] * (macro["gdp"]/data_yr["xgdpn"]) # Fed govnt expenditures
    dynamic["EGSE"] = sim_yr["egse"] * (macro["gdp"]/data_yr["xgdpn"]) # S&l govnt expenditures
    dynamic["EM"] = sim_yr["em"] * (macro["gdp"]/data_yr["xgdpn"]) # Imports
    dynamic["EX"] = sim_yr["ex"] * (macro["gdp"]/data_yr["xgdpn"]) # exports

    # Government Surplus and components #
    dynamic["GFSRPN"] = sim_yr["gfsrpn"] * (macro["gdp"]/data_yr["xgdpn"]) # Fed govnt surplus
    dynamic["GTN"] = sim_yr["gtn"] * (macro["gdp"]/data_yr["xgdpn"]) # Fed net transfer
    dynamic["GFINTN"] = sim_yr["gfintn"] * (macro["gdp"]/data_yr["xgdpn"]) # Fed net interest
    dynamic["EGFLN"] = sim_yr["egfln"] * (macro["gdp"]/data_yr["xgdpn"]) # Fed employee comp
    dynamic["EGFEN"] = sim_yr["egfen"] * (macro["gdp"]/data_yr["xgdpn"]) # Nominal Fed govnt expenditures

    # Tax rates #
    dynamic["TRP"] = sim_yr_avg["trp"]
    dynamic["TRCI"] = sim_yr_avg["trci"]

    dynamic["TRP_t"] = sim_yr_avg["trp_t"]
    dynamic["TRCI_t"] = sim_yr_avg["trci_t"]

    # Tax Base #
    dynamic["TRP_Base"] = (sim_yr["ypn"] - sim_yr["gtn"]) * (macro["gdp"]/data_yr["xgdpn"])
    dynamic["TRCI_Base"] = sim_yr["ynicpn"] * (macro["gdp"]/data_yr["xgdpn"])

    dynamic["TRP_Base"] = (sim_yr_avg["ypn"] - sim_yr_avg["gtn"]) 
    dynamic["TRCI_Base"] = sim_yr_avg["ynicpn"] 

    # Labor Force Variables #
    dynamic["LUR"] = sim_yr_avg["lur"] # unemployment rate 
    dynamic["LFPR"] = sim_yr_avg["lfpr"] # labor force participation rate
    dynamic["LEH"] = sim_yr_avg["leh"] # civilian employment

    # Inflation #
    dynamic["PICNIA"] = sim_yr_avg["picnia"] # PCE inflation rate

    # Interest Rates #
    dynamic["RFF"] = sim_yr_avg["rff"] # Fed Funds Rate
    dynamic["RTB"] = sim_yr_avg["rtb"] # 3 month treasury bill
    dynamic["RG10"] = sim_yr_avg["rg10"] # 10-yr rate

    dynamic.index = pandas.PeriodIndex(dynamic.index, freq = "Y")

    return(dynamic)

def denton_boot(Annual: array):
    #---------------------------------------------------------------------
    # This function takes in annual tax revenue data and interpolates it 
    # to quarterly frequency. This method smooths the new year step up.
    # Parameters:
    #   Annual (array): Annual tax revenue data of length T
    # Returns:
    #   out (array): Quarterly tax revenue data of length 4T
    #---------------------------------------------------------------------
    T = len(Annual)
    Tq = T * 4

    C = calc_c(Tq)
    J = calc_j(T)
    J_t = np.transpose(J * -1)
    zero4 = np.zeros((T,T))
    
    lhs1 = np.concatenate((C, J), axis=0)
    lhs2 = np.concatenate((J_t, zero4), axis=0)
    lhs = np.linalg.inv(np.concatenate((lhs1, lhs2), axis=1))   
    rhs = np.append(np.zeros(Tq), Annual)

    out = np.dot(lhs, rhs)
    return(out[0:Tq])

def calc_j(T: int):
    pattern = np.array([1,1,1,1])
    return(np.kron(np.eye(T), pattern))

def calc_c(Tq: int):
    #---------------------------------------------------------------------
    # This function creates a square band matrix for Denton interpolation
    # Parameters:
    #   Tq (int) : The number of quarters to be interpolated
    # Returns:
    #   C (numpy): A Tq X Tq band matrix
    #---------------------------------------------------------------------
    base = inner_band([2,-8,12,-8,2], Tq-4)
    v0 = np.zeros(Tq)
    v1 = np.zeros(Tq)
    np.put(v0, [0,1,2], [2,-4,2])
    np.put(v1, [0,1,2,3], [-4,10,-8,2])
    out = np.insert(base, 0, v1, axis=0)
    out = np.insert(out, 0, v0, axis=0)
    out = np.insert(out, len(out), np.flip(v1), axis=0)
    out = np.insert(out, len(out), np.flip(v0), axis=0)
    return(out)

def inner_band(a, W):
    # Thank you: http://scipy-lectures.org/advanced/advanced_numpy/#indexing-scheme-strides
    a = np.asarray(a)
    p = np.zeros(W-1,dtype=a.dtype)
    b = np.concatenate((p,a,p))
    s = b.strides[0]
    strided = np.lib.stride_tricks.as_strided
    return strided(b[W-1:], shape=(W,len(a)+W-1), strides=(-s,s))

