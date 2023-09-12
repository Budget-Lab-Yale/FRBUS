import pandas

from pandas import DataFrame, Period, PeriodIndex
from typing import Union

def levers(card: DataFrame, start: Union[str, Period], end: Union[str, Period], data: DataFrame, run: int):
    data.loc[start:end, "dfpdbt"] = card.loc[run, "dfpdbt"]
    data.loc[start:end, "dfpsrp"] = card.loc[run, "dfpsrp"]
    data.loc[start:end, "dfpex"] = card.loc[run, "dfpex"]
    data.loc[start:end, "dmptay"] = card.loc[run, "dmptay"]
    data.loc[start:end, "dmpintay"] = card.loc[run, "dmpintay"]
    return()

def sim_path(card: DataFrame, start: Union[str, Period], end: Union[str, Period], with_adds: DataFrame):
    #example 4 probably, so this would just be a wrapper for mcontrol?
    #ydn
    #ypn
    #tpn
    #yh

    return()