import pandas
import numpy

from pandas import DataFrame
from pyfrbus.load_data import load_data

from punchcard import read_gdp
from sim_setup import denton_boot

def dentonizer(data: DataFrame):
    out = pandas.DataFrame()

    for col in data.columns:
        out.loc[:, col] = denton_boot(data.loc[:,col].to_numpy())

    out.index = pandas.period_range(start=str(data.index[0])+"Q1", end = str(data.index[len(data)-1])+"Q4", freq="Q")

    return(out)