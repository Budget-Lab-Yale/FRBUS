import pandas
import numpy as np
import scipy

from pandas import DataFrame, Period, PeriodIndex, read_csv
from numpy import array
from typing import Union

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus

from punchcard import parse_tax_sim, read_gdp, gather_med


def levers(card: DataFrame, start: Union[str, Period], end: Union[str, Period], data: DataFrame, run: int):
    data.loc[start:end, "dfpdbt"] = card.loc[run, "dfpdbt"]
    data.loc[start:end, "dfpsrp"] = card.loc[run, "dfpsrp"]
    data.loc[start:end, "dfpex"] = card.loc[run, "dfpex"]
    data.loc[start:end, "dmptay"] = card.loc[run, "dmptay"]
    data.loc[start:end, "dmpintay"] = card.loc[run, "dmpintay"]
    return(data)

def build_data(card: DataFrame, run: int):

    longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "version"]), str(card.loc[run, "vintage"])), "LONGBASE.TXT")
    
    ts = parse_tax_sim(card, run, True)
    start = ts.index[0]
    end = ts.index[len(ts)-1]

    cbo = read_gdp(card.loc[run, "cbo_path"])
    cbo = cbo.iloc[start:end]
    cbo["TPN_ts"] = ts[["liab_iit_net"]] / cbo[["gdp"]]
 
    start = pandas.PeriodIndex(start, freq='Q')
    end = pandas.PeriodIndex(end, freq='Q') + 3

    cbo["TPN_ts"] = cbo["TPN_ts"] * (longbase.loc[start:end, "xgdp"].groupby("Year").sum() / 4)

    TPN_fs = (denton_boot(cbo["TPN_ts"].to_numpy)) * 4
    TRP_fs = TPN_fs / (longbase.loc[start:end, "ypn"] - longbase.loc[start:end, "gtn"])

    frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")
    longbase.loc[start:end, "dfpsrp"] = 1
    longbase.loc[start:end, "dmpintay"] = 1
    longbase.loc[start:end, "dmptay"] = 0
    with_adds = frbus.init_trac(start, end, longbase)
    with_adds.loc[start:end, "trp_t"] = TRP_fs

    out = frbus.mcontrol(start, end, with_adds, "trp", "trp_t", "trp_aerr")

    return(out)

def calc_trp_path(card: DataFrame, run: int, data: DataFrame):
    ts = parse_tax_sim(card, run, False)
    start = ts.index[0]
    end = ts.index[len(ts)-1]

    cbo = read_gdp(card.loc[run, "cbo_path"])
    cbo = cbo.iloc[start:end]
    cbo["TPN_ts"] = ts[["liab_iit_net"]] / cbo[["gdp"]]

    
    start = pandas.PeriodIndex(start, freq='Q')
    end = pandas.PeriodIndex(end, freq='Q') + 3

    cbo["TPN_ts"] = cbo["TPN_ts"] * (data.loc[start:end, "xgdp"].groupby("Year").sum() / 4)

    TPN_fs = (denton_boot(cbo["TPN_ts"].to_numpy)) * 4
    TRP_fs = TPN_fs / (data.loc[start:end, "ypn"] - data.loc[start:end, "gtn"])

    return(TRP_fs)

def denton_boot(TPN_ts: array):
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
    base = inner_band([2,-8,12,-8,2], Tq-4)
    v0 = np.array([0] * Tq)
    v1 = np.array([0] * Tq)
    np.put(v0, [0,1,2], [2,-4,2])
    np.put(v1, [0,1,2,3], [-4,10,-8,2])
    out = np.insert(base, 0, v1, axis=0)
    out = np.insert(out, 0, v0, axis=0)
    out = np.insert(out, len(out), np.flip(v1), axis=0)
    out = np.insert(out, len(out), np.flip(v0), axis=0)
    return(out)

def inner_band(a, W):
    # Thank you:
    # http://scipy-lectures.org/advanced/advanced_numpy/#indexing-scheme-strides
    a = np.asarray(a)
    p = np.zeros(W-1,dtype=a.dtype)
    b = np.concatenate((p,a,p))
    s = b.strides[0]
    strided = np.lib.stride_tricks.as_strided
    return strided(b[W-1:], shape=(W,len(a)+W-1), strides=(-s,s))

def calc_marginal(card: DataFrame, run: int, y_path: str = None):
    
    
    if(brackets is None):
        brackets = np.array([11000,44725,95375,182100,231250,578125])
    if(rates is None):
        rates = np.array([10,12,22,24,32,35,37])

    
    return(marginal)