import pandas
import datetime
import pyfrbus
import sys
import os

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import build_data, calc_tpn_path

#can move into loop if we want a vintage stamp for every model run
ct = datetime.datetime.now()
stamp = str(ct.year)+str(ct.month)+str(ct.day)+str(ct.hour)

card = pandas.read_csv(sys.argv[1])

data = build_data(card, 0)

#frbus = Frbus(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "version"]), str(card.loc[run, "vintage"]), "model.xml"))
frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml")

# FLAG
start = pandas.Period("2017Q1", freq="Q") #data.index[0]
end = pandas.Period("2033Q4", freq="Q")#data.index[len(data)-1]

for run in range(1, len(card)):
    start = card.loc[run, "start"]
    end = card.loc[run, "end"]
    
    with_adds = frbus.init_trac(start, end, data)

    with_adds.loc[start:end, "tpn_t"] = calc_tpn_path(card, run, with_adds)

    sim = frbus.mcontrol(start, end, with_adds, targ=["tpn"], traj=["tpn_t"], inst=["trp_aerr"])
