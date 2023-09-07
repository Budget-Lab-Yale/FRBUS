import os
import pandas
import numpy

from pandas import DataFrame, Period, PeriodIndex, read_csv
from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus, init_trac


#INSTEAD, HAVE A MASTER THAT READS IN THE RUNSCRIPT AND CREATES ALL THE PAIRS

#OR, DEFINE A WRITER CLASS THAT IS INITIALIZED WITH RUNSCRIPT, AND THE USERS REFERENCE IT TO DO IO

# Do testing once FRBUS file directories are setup
def punchcard(filename: str) -> DataFrame:
    return(pandas.read_csv(filename, index_col=0))

def ybl_load_data(directory_name: str) -> DataFrame:
    guide = os.path.join("../../raw_data/FRBUS", directory_name, "LONGBASE.TXT")
    return load_data(guide)

def ybl_Frbus(directory_name: str) -> Frbus:
    guide = os.path.join("../../raw_data/FRBUS", directory_name, "model.xml")
    return Frbus(guide)

#THIS IS FOR INIT TRAC
#EDIT FOR ITER?
def ybl_punchcard(filename: str) -> DataFrame:
    punchcard = read_csv(filename)
    #If the python script lives in the same folder as the raw_data
    data = load_data("LONGEBASE.TXT")
    frbus = Frbus("model.xml")
    #If it doesn't
    #data = load_data("../../raw_data/FRBUS/punchcard[1,"ybl_frbus.version"]/punchcard[1,"ybl_frbus.vintage"]/LONGBASE.TXT")
    #frbus = Frbus("../../raw_data/FRBUS/punchcard[1,"ybl_frbus.version"]/punchcard[1,"ybl_frbus.vintage"]/model.xml")
    start = pandas.Period(punchcard[1, "start"])
    end = pandas.Period(punchcard[1, "end"])

    data.loc[start:end, "dfpdbt"] = punchcard[1, "dfpdbt"]
    data.loc[start:end, "dfpsrp"] = punchcard[1, "dfpsrp"]
    data.loc[start:end, "dfpex"] = punchcard[1, "dfpex"]
    data.loc[start:end, "dmptay"] = punchcard[1, "dmptay"]
    data.loc[start:end, "dmpintay"] = punchcard[1, "dmpintay"]

    return(frbus.init_trac(start, end, data))


def run_out(filename_base: str, filename_sim: str, directory: str, baseline: DataFrame, sim: DataFrame):
    #Create base path
    path = os.path.join("../../model_data/FRBUS",directory)
    #Check if path exists, create if it doesn't
    if not os.path.exists(path):
        os.mkdir(path)
    #Write
    baseline.to_csv(os.path.join(path, filename_base+".csv"))
    sim.to_csv(os.path.join(path, filename_sim+".csv"))
    return()


def run_out(baseline: DataFrame, sim: DataFrame, vars: Optional[list]=None):
    path = os.path.join("../")
    if vars is not None:
        out = baseline.loc[start-6:end, vars]
        out.to_csv(os.path.join(path, "baseline.csv"))
        out = sim.loc[start-6:end, vars]
        out.to_csv(os.path.join(path, "sim.csv"))
        return()

    else:
        out = baseline.loc[start-6:end, vars]
        out.to_csv(os.path.join(path, "baseline.csv"))
        out = sim.loc[start-6:end, vars]
        out.to_csv(os.path.join(path, "sim.csv"))
        return()
