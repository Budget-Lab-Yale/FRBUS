import pandas
import numpy as np

from pandas import DataFrame, Period, PeriodIndex, read_csv
from typing import Union
from pyfrbus.load_data import load_data
from punchcard import parse_tax_sim

def levers(card: DataFrame, start: Union[str, Period], end: Union[str, Period], data: DataFrame, run: int):
    data.loc[start:end, "dfpdbt"] = card.loc[run, "dfpdbt"]
    data.loc[start:end, "dfpsrp"] = card.loc[run, "dfpsrp"]
    data.loc[start:end, "dfpex"] = card.loc[run, "dfpex"]
    data.loc[start:end, "dmptay"] = card.loc[run, "dmptay"]
    data.loc[start:end, "dmpintay"] = card.loc[run, "dmpintay"]
    return(data)


def apply_tax_delta(card: DataFrame, run: int, start: Union[str, Period], end: Union[str, Period], with_adds: DataFrame):
    tax_sim_data_b = parse_tax_sim(card, run, True)
    tax_sim_data_s = parse_tax_sim(card, run, False)

    with_adds.loc[start:end, "trp_aerr"] += calc_trp_shock(tax_sim_data_b, tax_sim_data_s, with_adds, start-12, start-1) * 4

    return(with_adds)


def calc_trp_shock(tax_sim_data_b: DataFrame, tax_sim_data_s: DataFrame, with_adds: DataFrame, f_start: Union[str, Period], f_end: Union[str, Period]):

    F = calc_f(tax_sim_data_b.loc[f_start:f_end, "liab_iit"], with_adds.loc[f_start:f_end, "tpn"])

    ts_rev = tax_sim_data_s["liab_iit_net"] - tax_sim_data_b["liab_iit_net"]
    denom = (with_adds["ypn"] - with_adds["gtn"])
    
    trp_shock_yr = (F * ts_rev)/denom
    with_adds["trp"] = with_adds["trp"]/4
    trp_yr = (with_adds.groupby("Year")["trp"].sum()) + trp_shock_yr
    
    return(denton(np.array(with_adds["trp"]), np.array(trp_yr)) - with_adds["trp"])


def calc_f(tax_sim_data_b: DataFrame, with_adds: DataFrame):
    with_adds["tpn"] = with_adds["tpn"]/4
    tpn_yr = with_adds.groupby("Year")["tpn"].sum()
    return(sum(tpn_yr/tax_sim_data_b["liab_iit"])/len(tpn_yr))

def denton(I: np.array, A: np.array):
    # This code is a modified version of the function found here: https://github.com/MaxLugo/denton
    # It is unavailable using conda and challenging to install through the back door.
    # Max Lugo deserves full credit.

    len_A, len_I, q = len(A), len(I), int(len(I)/len(A)) 
    I_tilde = np.linalg.pinv(np.diag(I))
    I, A = I[:, np.newaxis], A[:, np.newaxis]

    D = -1 * np.eye(len_I)
    D[-1, -1] = 0
    for i in range(len(D)-1):
        D[i, i+1] = 1

    J = np.zeros((len_A, len_I))
    for j in range(len(J)):
        J[j, j*q:j*q + q] = [1]*q

    M = I_tilde.T @ D.T @ D @ I_tilde
    r1, r2 = np.concatenate((M + M.T, -J.T), axis=1), np.concatenate((J, np.zeros((len_A, len_A))), axis=1)
    Z = np.concatenate((r1, r2), axis=0)
    X_lambda = np.linalg.pinv(Z) @ np.concatenate((np.zeros((len_I ,1)), A), axis=0)
    X = X_lambda[:-len_A]
    rv = X
    return rv

def sim_path(tax_sim_data: DataFrame, start: Union[str, Period], end: Union[str, Period], with_adds: DataFrame):
        
    with_adds.loc[start:end, "gtn_t"] = denton(
        np.array(with_adds[start:end, "gtn"]), 
        np.array(tax_sim_data[["gtn"]])
    )
    with_adds.loc[start:end, "trp_t"] = denton(
        np.array(with_adds[start:end, "trp"]), 
        np.array(tax_sim_data[["trp"]])
    )



    return(with_adds)

