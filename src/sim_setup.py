import pandas

from pandas import DataFrame, Period, PeriodIndex, read_csv
from typing import Union
from pyfrbus.load_data import load_data

def levers(card: DataFrame, start: Union[str, Period], end: Union[str, Period], data: DataFrame, run: int):
    data.loc[start:end, "dfpdbt"] = card.loc[run, "dfpdbt"]
    data.loc[start:end, "dfpsrp"] = card.loc[run, "dfpsrp"]
    data.loc[start:end, "dfpex"] = card.loc[run, "dfpex"]
    data.loc[start:end, "dmptay"] = card.loc[run, "dmptay"]
    data.loc[start:end, "dmpintay"] = card.loc[run, "dmpintay"]
    return()

def sim_path(card: DataFrame, run: int, start: Union[str, Period], end: Union[str, Period], with_adds: DataFrame):
    with_adds.loc[start, card.loc[run, "shock"]] += card.loc[run, "shockby"]
    """
    guide = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS", str(card.loc[run, "version"]), str(card.loc[run, "vintage"]), "shocks.csv")
    shocks = load_data(guide)

    for col in shocks.columns:
        with_adds.loc[start:end, col] = shocks[col]    
    """
    return(with_adds)