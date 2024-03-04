import pandas
import numpy as np
import scipy
import os

from pandas import DataFrame, Period, PeriodIndex, read_csv
from numpy import array
from typing import Union
from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from punchcard import parse_tax_sim, read_gdp, parse_corp_sim


def levers(card: DataFrame, start: Union[str, Period], end: Union[str, Period], data: DataFrame, run: int):
    data.loc[start:end, "dfpdbt"] = card.loc[run, "dfpdbt"]
    data.loc[start:end, "dfpsrp"] = card.loc[run, "dfpsrp"]
    data.loc[start:end, "dfpex"] = card.loc[run, "dfpex"]
    data.loc[start:end, "dmptay"] = card.loc[run, "dmptay"]
    data.loc[start:end, "dmpintay"] = card.loc[run, "dmpintay"]
    return(data)

def build_data(card: DataFrame, run: int, raw = False, card_dates = False):
    #---------------------------------------------------------------------
    # This function constructs a baseline dataset using the mcontrol protocol
    # against which alternate scenario runs are compared. 
    # Parameters:
    #   card (DataFrame): Punchcard of test specific parameters
    #   run  (int)      : Row for the card dataframe. Should always be 1.
    #   raw  (bool)     : Flag for if the baseline is constructed by YBL or the FOMC
    # Returns:
    #   longbase (DataFrame): FRB longbase.txt file adjusted to suit this 
    #                         specific policy test.
    #---------------------------------------------------------------------
    if raw:
        longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))
    else:
        longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/Baselines", str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))

    ts = parse_tax_sim(card, run, True)

    if card_dates:
        start = pandas.Period(card.loc[run, "start"][0:4], freq="Y")
        end = pandas.Period(card.loc[run, "end"][0:4], freq="Y")
    else:
        start = ts.index[0]
        end = ts.index[len(ts)-1]

    cs = parse_corp_sim(card, run)
    
    cbo = read_gdp(card.loc[run, "cbo_path"])
    cbo = cbo.loc[start:end,:]
    cbo['TPN_ts'] = ts["liab_iit_net"] / cbo["gdp"]
    cbo['TCIN_cs'] = cs["TCIN"] / cbo["gdp"]

    per_mtr = read_csv("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/housing_subsidy_rates.csv", index_col=0)
    per_mtr = per_mtr.loc[2017:2047,:]
    corp_mtr = read_csv("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/mtr_corp_rates.csv", index_col=0)
    corp_mtr = corp_mtr.loc[2017:2047,:]

    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    temp = longbase.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = cbo.index
    cbo["TPN_ts"] *= temp
    cbo["TCIN_cs"] *= temp 

    TPN_fs = denton_boot(cbo["TPN_ts"].to_numpy())
    TCIN_fs = denton_boot(cbo["TCIN_cs"].to_numpy())
    TRFPM_fs = (denton_boot(per_mtr["mtr_law2017"].to_numpy())) * -1 *4
    TRFCIM_fs = denton_boot(corp_mtr["mtr_law2017"].to_numpy()) * 4


    frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")
    longbase.loc[start:end, "dfpsrp"] = 1
    longbase.loc[start:end, "dfpdbt"] = 0
    longbase.loc[start:end, "dfpex"] = 0

    longbase.loc[start-100:, 'dfpdbt'] = 0
    longbase.loc[start-100:end, 'dfpex'] = 1
    longbase.loc[start-100:end, 'dfpsrp'] = 0
    longbase.loc[end+1:, 'dfpsrp'] = 1

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

    with_adds = frbus.init_trac(start, end, longbase)
    with_adds.loc[start:end, "tpn_t"] = TPN_fs
    with_adds.loc[start:end, "tcin_t"] = TCIN_fs
    #with_adds.loc[start:end, "trfpm_t"] = TRFPM_fs
    #with_adds.loc[start:end, "trfcim_t"] = TRFCIM_fs

    with_adds.loc[start:end, "trfpm"] = TRFPM_fs
    with_adds.loc[start:end, "trfcim"] = TRFCIM_fs

    out = frbus.mcontrol(start, end, with_adds, \
        targ=["tpn", "tcin"], \
        traj=["tpn_t", "tcin_t"], \
        inst=["trp_aerr", "trci_aerr"])

    out = out.filter(regex="^((?!_).)*$")

    longbase.loc[start:end,:] = out.loc[start:end,:]
    return(longbase)

def calc_tpn_path(card: DataFrame, run: int, data: DataFrame, card_dates = False):
    ts = parse_tax_sim(card, run, False)
    
    if card_dates:
        start = pandas.Period(card.loc[run, "start"][0:4], freq="Y")
        end = pandas.Period(card.loc[run, "end"][0:4], freq="Y")
    
    else:
        start = ts.index[0]
        end = ts.index[len(ts)-1]

    cbo = read_gdp(card.loc[run, "cbo_path"])
    cbo = cbo.loc[start:end]
    cbo['TPN_ts'] = ts["liab_iit_net"] / cbo["gdp"]
    
    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    temp = data.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = cbo.index
    cbo["TPN_ts"] *= temp

    TPN_fs = (denton_boot(cbo["TPN_ts"].to_numpy()))
    
    return(TPN_fs)

def calc_tcin_path(card: DataFrame, run: int, data: DataFrame, card_dates = False):
    cs = parse_corp_sim(card, run)

    if card_dates:
        start = pandas.Period(card.loc[run, "start"][0:4], freq="Y")
        end = pandas.Period(card.loc[run, "end"][0:4], freq="Y")

    else:
        start = cs.index[0]
        end = cs.index[len(cs)-1]

    cbo = read_gdp(card.loc[run, "cbo_path"])
    cbo = cbo.loc[start:end]
    cs = cs.loc[start:end]
    cbo['TCIN_cs'] = cs["TCIN"] / cbo["gdp"]

    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    temp = data.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = cbo.index
    cbo["TCIN_cs"] *= temp

    TCIN_fs = (denton_boot(cbo["TCIN_cs"].to_numpy()))
    
    return(TCIN_fs)

def dynamic_rev(card: DataFrame, run: int, start: Period, end: Period, data: DataFrame,  frbus: Frbus, delta=False):
    cbo = read_gdp(card.loc[run, "cbo_path"])
    #start_cbo = pandas.Period(str(start.year), freq="Y")
    #end_cbo = pandas.Period(str(end.year), freq="Y")

    per_mtr = read_csv("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/housing_subsidy_rates.csv", index_col=0)
    per_mtr = per_mtr.loc[2017:2027,:]
    corp_mtr = read_csv("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/mtr_corp_rates.csv", index_col=0)
    corp_mtr = corp_mtr.loc[2017:2027,:]

    if delta:
        data.loc[start:end, "trp_t"] = ((data.loc[start:end, "tpn_d"]*4 + calc_tpn_path(card, run, data, True)) / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"]))
        data.loc[start:end, "trci_t"] = (data.loc[start:end, "tcin_d"]*4 + calc_tcin_path(card, run, data, True)) / data.loc[start:end, "ynicpn"]
        data.loc[start:end, "trfpm"] = (denton_boot(per_mtr["mtr_tcja"].to_numpy())) * -1 * 4
        data.loc[start:end, "trfcim"] = denton_boot(corp_mtr["mtr_tcja"].to_numpy()) * 4

    else:
        data.loc[start:end, "trp_t"] = (calc_tpn_path(card, run, data, True)) / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"])
        data.loc[start:end, "trci_t"] = (calc_tcin_path(card, run, data, True)) / data.loc[start:end, "ynicpn"]
        data.loc[start:end, "trfpm"] = (denton_boot(per_mtr["mtr_law2017"].to_numpy())) * -1 * 4
        data.loc[start:end, "trfcim"] = denton_boot(corp_mtr["mtr_law2017"].to_numpy()) * 4

    sim = frbus.mcontrol(start, end, data, \
        targ=["trp", "trci"], \
        traj=["trp_t", "trci_t"], \
        inst=["trp_aerr", "trci_aerr"])

    data_yr = data.groupby(data.index.year).sum()
    sim_yr  = sim.groupby(sim.index.year).sum()
    sim_yr_avg  = sim.groupby(sim.index.year).mean() #for variables not converted between CBO/FRBUS $

    cbo = cbo.loc[start.asfreq('Y'):end.asfreq('Y'),]
    data_yr = data_yr.loc[start.year:end.year,]
    sim_yr = sim_yr.loc[start.year:end.year,]
    sim_yr_avg = sim_yr_avg.loc[start.year:end.year,]

    cbo.index = data_yr.index

    dynamic = pandas.DataFrame()
    dynamic["TPN"] =  sim_yr["tpn"] * (cbo["gdp"]/data_yr["xgdpn"])
    dynamic["TCIN"] = sim_yr["tcin"] * (cbo["gdp"]/data_yr["xgdpn"])

    ### Adding other variables of interest for output ####


    # Real GDP and its components #
    dynamic["XGDPN"] = sim_yr["xgdpn"] * (cbo["gdp"]/data_yr["xgdpn"]) # Real GDP
    dynamic["XGDP"] = sim_yr["xgdp"] * (cbo["gdp"]/data_yr["xgdpn"]) # Real GDP
    dynamic["ECNIA"] = sim_yr["ecnia"] * (cbo["gdp"]/data_yr["xgdpn"]) # PCE
    dynamic["EBFI"] = sim_yr["ebfi"] * (cbo["gdp"]/data_yr["xgdpn"]) # Bus Fixed Investment
    dynamic["EH"] = sim_yr["eh"] * (cbo["gdp"]/data_yr["xgdpn"]) # Residential investment
    dynamic["EGFE"] = sim_yr["egfe"] * (cbo["gdp"]/data_yr["xgdpn"]) # Fed govnt expenditures
    dynamic["EGSE"] = sim_yr["egse"] * (cbo["gdp"]/data_yr["xgdpn"]) # S&l govnt expenditures
    dynamic["EM"] = sim_yr["em"] * (cbo["gdp"]/data_yr["xgdpn"]) # Imports
    dynamic["EX"] = sim_yr["ex"] * (cbo["gdp"]/data_yr["xgdpn"]) # exports

    # Real GDP component Price Indices #
    dynamic["PGDP"] = sim_yr_avg["pgdp"]
    dynamic["PCNIA"] = sim_yr_avg["pcnia"]
    dynamic["PKBFIR"] = sim_yr_avg["pkbfir"]
    dynamic["PXP"] = sim_yr_avg["pxp"]
    dynamic["PHR"] = sim_yr_avg["phr"]
    dynamic["PEGFR"] = sim_yr_avg["pegfr"]
    dynamic["PXR"] = sim_yr_avg["pxr"]
    dynamic["PMO"] = sim_yr_avg["pmo"]


    # Government Surplus and components #
    dynamic["GFSRPN"] = sim_yr["gfsrpn"] * (cbo["gdp"]/data_yr["xgdpn"]) # Fed govnt surplus
    dynamic["GTN"] = sim_yr["gtn"] * (cbo["gdp"]/data_yr["xgdpn"]) # Fed net transfer
    dynamic["GFINTN"] = sim_yr["gfintn"] * (cbo["gdp"]/data_yr["xgdpn"]) # Fed net interest
    dynamic["EGFLN"] = sim_yr["egfln"] * (cbo["gdp"]/data_yr["xgdpn"]) # Fed employee comp
    dynamic["EGFEN"] = sim_yr["egfen"] * (cbo["gdp"]/data_yr["xgdpn"]) # Nominal Fed govnt expenditures

    # Tax rates #
    dynamic["TRP"] = sim_yr_avg["trp"]
    dynamic["TRCI"] = sim_yr_avg["trci"]

    dynamic["TRP_t"] = sim_yr_avg["trp_t"]
    dynamic["TRCI_t"] = sim_yr_avg["trci_t"]

    dynamic["TRFPM"] = sim_yr_avg["trfpm"]
    dynamic["TRFCIM"] = sim_yr_avg["trfcim"]

    # Cost of investment #
    dynamic["RCCH"] = sim_yr_avg["rcch"]
    dynamic["RBFI"] = sim_yr_avg["rbfi"]
    dynamic["RTBFI"] = sim_yr_avg["rtbfi"]

    # Tax Base #
    #dynamic["TRP_Base"] = (sim_yr["ypn"] - sim_yr["gtn"]) * (cbo["gdp"]/data_yr["xgdpn"])
    #dynamic["TRCI_Base"] = sim_yr["ynicpn"] * (cbo["gdp"]/data_yr["xgdpn"])

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

def denton_boot(TPN_ts: array):
    #---------------------------------------------------------------------
    # This function takes in annual tax revenue data and interpolates it 
    # to quarterly frequency. This method smooths the new year step up.
    # Parameters:
    #   TPN_ts (array): Annual tax revenue data of length T
    # Returns:
    #   out (array): Quarterly tax revenue data of length 4T
    #---------------------------------------------------------------------
    T = len(TPN_ts)
    Tq = T * 4

    C = calc_c(Tq)
    J = calc_j(T)
    J_t = np.transpose(J * -1)
    zero4 = np.zeros((T,T))
    
    lhs1 = np.concatenate((C, J), axis=0)
    lhs2 = np.concatenate((J_t, zero4), axis=0)
    lhs = np.linalg.inv(np.concatenate((lhs1, lhs2), axis=1))   
    rhs = np.append(np.zeros(Tq), TPN_ts)

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