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

def build_data(card: DataFrame, run: int):
    #---------------------------------------------------------------------
    # This function constructs a baseline dataset using the mcontrol protocol
    # against which alternate scenario runs are compared. 
    # Parameters:
    #   card (DataFrame): Punchcard of test specific parameters
    #   run  (int)      : Row for the card dataframe. Should always be 1.
    # Returns:
    #   longbase (DataFrame): FRB longbase.txt file adjusted to suit this 
    #                         specific policy test.
    #---------------------------------------------------------------------
    longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))

    ts = parse_tax_sim(card, run, True)
    start = ts.index[0]
    end = ts.index[len(ts)-1]

    cs = parse_corp_sim(card, run)
    
    cbo = read_gdp(card.loc[run, "cbo_path"])
    cbo = cbo.loc[start:end]
    cbo['TPN_ts'] = ts["liab_iit_net"] / cbo["gdp"]
    cbo['TCIN_cs'] = cs["TCIN"] / cbo["gdp"]

    start = start.asfreq('Q') - 3
    end = end.asfreq('Q')

    temp = longbase.loc[start:end, "xgdpn"]
    temp = temp.groupby(temp.index.year).sum() 
    temp.index = cbo.index
    cbo["TPN_ts"] *= temp
    cbo["TCIN_cs"] *= temp 

    TPN_fs = denton_boot(cbo["TPN_ts"].to_numpy())
    TCIN_fs = denton_boot(cbo["TCIN_cs"].to_numpy())

    frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")
    longbase.loc[start:end, "dfpsrp"] = 1
    longbase.loc[start:end, "dfpdbt"] = 0
    longbase.loc[start:end, "dfpex"] = 0

    longbase.loc[start:end, "dmpintay"] = 1
    longbase.loc[start:end, "dmptay"] = 0

    with_adds = frbus.init_trac(start, end, longbase)
    with_adds.loc[start:end, "tpn_t"] = TPN_fs
    with_adds.loc[start:end, "tcin_t"] = TCIN_fs

    out = frbus.mcontrol(start, end, with_adds, targ=["tpn", "tcin"], traj=["tpn_t", "tcin_t"], inst=["trp_aerr", "trci_aerr"])
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
    start_cbo = pandas.Period(str(start.year), freq="Y")
    end_cbo = pandas.Period(str(end.year), freq="Y")

    if delta:
        data.loc[start:end, "trp_t"] = ((data.loc[start:end, "tpn_d"] + calc_tpn_path(card, run, data, True)) / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"]))
        data.loc[start:end, "trci_t"] = (data.loc[start:end, "tcin_d"] + calc_tcin_path(card, run, data, True)) / data.loc[start:end, "ynicpn"]

    else:
        data.loc[start:end, "trp_t"] = (calc_tpn_path(card, run, data, True)) / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"])
        data.loc[start:end, "trci_t"] = (calc_tcin_path(card, run, data, True)) / data.loc[start:end, "ynicpn"]
    
    sim = frbus.mcontrol(start, end, data, targ=["trp", "trci"], traj=["trp_t", "trci_t"], inst=["trp_aerr", "trci_aerr"])

    data_yr = data.groupby(data.index.year).sum()
    sim_yr  = sim.groupby(sim.index.year).sum()

    cbo = cbo.loc[start_cbo:end_cbo,]
    data_yr = data_yr.loc[start.year:end.year,]
    sim_yr = sim_yr.loc[start.year:end.year,]

    cbo.index = data_yr.index

    dynamic = pandas.DataFrame()
    dynamic["TPN"] =  sim_yr["tpn"] * (cbo["gdp"]/data_yr["xgdpn"])
    dynamic["TCIN"] = sim_yr["tcin"] * (cbo["gdp"]/data_yr["xgdpn"])

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

