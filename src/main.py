import pandas
import datetime
import pyfrbus
import sys
import os

from punchcard import parse_tax_sim, run_out
from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import build_data, calc_trp_path

#can move into loop if we want a vintage stamp for every model run
ct = datetime.datetime.now()
stamp = str(ct.year)+str(ct.month)+str(ct.day)+str(ct.hour)

card = pandas.read_csv(sys.argv[1])

data = build_data(card, 0, True)

frbus = Frbus(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "version"]), str(card.loc[run, "vintage"]), "model.xml"))

# FLAG
start = data.index[0]
end = data.index[len(data)-1]

for run in range(1, len(card)):

    rd_root = os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "version"]), str(card.loc[run, "vintage"]))
    md_root = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS", str(card.loc[run, "version"]), str(card.loc[run, "vintage"]))

    start = pandas.Period(card.loc[run, "start"])
    end = pandas.Period(card.loc[run, "end"])

    data = levers(card, start, end, data, run)

    with_adds = frbus.init_trac(start, end, data)

    with_adds.loc[start:end, "trp_t"] = calc_trp_path(card, run, with_adds)

    sim = frbus.mcontrol(start, end, with_adds, "trp", "trp_t", "trp_aerr")

    run_out(card, stamp, run, with_adds.loc[start-6:end], sim.loc[start-6:end])