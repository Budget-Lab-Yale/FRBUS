import pandas
import datetime
import pyfrbus
import sys
import os

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import build_data, dynamic_rev

ct = datetime.datetime.now()
stamp = str(ct.year)+str(ct.month)+str(ct.day)+str(ct.hour)

card = pandas.read_csv(sys.argv[1])

data = build_data(card, 0)

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")

for run in range(1, len(card)):
    start = card.loc[run, "start"]
    end = card.loc[run, "end"]
    
    data.loc[start:end, 'dfpdbt'] = 0
    data.loc[start:end, 'dfpex'] = 0
    data.loc[start:end, 'dfpsrp'] = 1

    data.loc[start:, "dmpintay"] = 1
    data.loc[start:, "dmptay"] = 0
    data.loc[start:, "dmpalt"] = 0
    data.loc[start:, "dmpex"] = 0
    data.loc[start:, "dmprr"] = 0
    data.loc[start:, "dmptlr"] = 0
    data.loc[start:, "dmptlur"] = 0
    data.loc[start:, "dmptmax"] = 0
    data.loc[start:, "dmptpi"] = 0
    data.loc[start:, "dmptr"] = 0
    data.loc[start:, "dmptrsh"] = 0

    with_adds = frbus.init_trac(start, end, data)

    dynamic = dynamic_rev(card, run, start, end, with_adds, frbus)