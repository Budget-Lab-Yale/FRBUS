import pandas
import numpy

from pandas import DataFrame
from pyfrbus.load_data import load_data

from sim_setup import denton_boot

def dentonizer(data: DataFrame):
    out = pandas.DataFrame()

    for col in data.columns:
        out.loc[:, col] = denton_boot(data.loc[:,col].to_numpy())

    out.index = pandas.period_range(start=str(data.index[0])+"Q1", end = str(data.index[len(data)-1])+"Q4", freq="Q")

    return(out)

def calc_delta(base: DataFrame, sim: DataFrame):
    delta = pandas.DataFrame()

    for col in base.columns:
        delta.loc[:, col] = sim.loc[:, col] - base.loc[:, col]
    
    return(delta)