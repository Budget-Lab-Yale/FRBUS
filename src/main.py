import pandas
import datetime
import pyfrbus
import sys
import os

from punchcard import ybl_Frbus, ybl_load_data, run_out
from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import levers, sim_path

#can move into loop if we want a vintage stamp for every model run
ct = datetime.datetime.now()
stamp = str(ct.year)+str(ct.month)+str(ct.day)+str(ct.hour)

card = pandas.read_csv(sys.argv[1])


for run in range(card.shape[0]):

    rd_root = os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "version"]), str(card.loc[run, "vintage"]))
    md_root = os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS", str(card.loc[run, "version"]), str(card.loc[run, "vintage"]))

    #data = ybl_load_data(rd_root)
    data = load_data(os.path.join(rd_root, "LONGBASE.TXT"))

    #frbus = ybl_Frbus(card.loc[run, "version"], card.loc[run, "vintage"])
    frbus = Frbus(os.path.join(rd_root, "model.xml"))

    start = pandas.Period(card.loc[run, "start"])
    end = pandas.Period(card.loc[run, "end"])

    levers(card, start, end, data, run)

    with_adds = frbus.init_trac(start, end, data)

    with_adds = sim_path(card, run, start, end, with_adds)

    sim = frbus.solve(start, end, with_adds)

    run_out(card, stamp, run, with_adds.loc[start-6:end], sim.loc[start-6:end])