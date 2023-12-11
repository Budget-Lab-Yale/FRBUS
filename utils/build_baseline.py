import pandas
import datetime
import pyfrbus
import sys
import os

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import denton_boot
from punchcard import parse_tax_sim, read_gdp
from pyfrbus.sim_lib import sim_plot

ct = datetime.datetime.now()
stamp = str(ct.year)+str(ct.month)+str(ct.day)

card = pandas.read_csv(sys.argv[1])
run = 0

longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))

ts = parse_tax_sim(card, run, True)
ts = ts[-31:]

start = pandas.Period("2023")
end = pandas.Period("2053")
end_long = end + 4*0

cbo = read_gdp(card.loc[run, "cbo_path"])
cbo = cbo.loc[start:end]
cbo['TPN_ts'] = ts["liab_iit_net"] / cbo["gdp"]

start = start.asfreq('Q') - 3
end = end.asfreq('Q')

temp = longbase.loc[start:end, "xgdpn"]
temp = temp.groupby(temp.index.year).sum() 
temp.index = cbo.index
cbo["TPN_ts"] *= temp

TPN_fs = (denton_boot(cbo["TPN_ts"].to_numpy()))

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")
longbase.loc[start-100:end_long+100, 'dfpdbt'] = 0
longbase.loc[start-100:end, 'dfpex'] = 1
longbase.loc[start-100:end, 'dfpsrp'] = 0
longbase.loc[end+1:end_long+100, 'dfpsrp'] = 1

longbase.loc[start:end_long+100, "dmpintay"] = 1
longbase.loc[start:end_long+100, "dmptay"] = 0
longbase.loc[start:end_long+100, "dmpalt"] = 0
longbase.loc[start:end_long+100, "dmpex"] = 0
longbase.loc[start:end_long+100, "dmprr"] = 0
longbase.loc[start:end_long+100, "dmptlr"] = 0
longbase.loc[start:end_long+100, "dmptlur"] = 0
longbase.loc[start:end_long+100, "dmptmax"] = 0
longbase.loc[start:end_long+100, "dmptpi"] = 0
longbase.loc[start:end_long+100, "dmptr"] = 0
longbase.loc[start:end_long+100, "dmptrsh"] = 0

with_adds = frbus.init_trac(start, end, longbase)
with_adds.loc[start:end, "tpn_t"] = TPN_fs + with_adds.loc[start:end, "egsen"]
with_adds.loc[start:end, "xgdp_t"] = with_adds.loc[start:end, "xgdp"]

out = frbus.mcontrol(start, end, with_adds, targ=["tpn", "xgdp"], traj=["tpn_t", "xgdp_t"], inst=["trp_aerr", "eco_aerr"])

out = out.filter(regex="^((?!_).)*$")

longbase.loc[start:end,:] = out.loc[start:end,:]

longbase.to_csv(f"/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS/v1/{stamp}/LONGBASE.TXT", index=True)
