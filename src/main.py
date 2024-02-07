import pandas
import datetime
import pyfrbus
import sys
import os


from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import build_data, dynamic_rev

stamp = datetime.datetime.now().strftime('%Y%m%d%H')

card = pandas.read_csv(sys.argv[1])

data = build_data(card, 0)

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")

for run in range(1, len(card)):
    start = card.loc[run, "start"]
    end = card.loc[run, "end"]
    
    with_adds = frbus.init_trac(start, end, data)

    dynamic = dynamic_rev(card, run, start, end, with_adds, frbus)