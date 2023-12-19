import pandas
import datetime
import pyfrbus
import sys
import os

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import denton_boot
from punchcard import parse_tax_sim, read_gdp, parse_corp_sim
from pyfrbus.sim_lib import sim_plot

ct = datetime.datetime.now()
stamp = str(ct.year)+str(ct.month)+str(ct.day)+str(ct.hour)+" TEST"

card = pandas.read_csv(sys.argv[1])
run = 0

longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))

ts = parse_tax_sim(card, run, True)
ts = ts[-31:]

cs = parse_corp_sim(card, run)

start = pandas.Period("2023")
end = pandas.Period("2053")
end_long = end + 4*10

cbo = read_gdp(card.loc[run, "cbo_path"])
cbo = cbo.loc[start:end]
cbo['TPN_ts'] = ts["liab_iit_net"] / cbo["gdp"]
cbo['TCIN_cs'] = cs["TCIN"] / cbo["gdp"]
#cbo['TCIN_cs'] = cbo["rev_corp"] / cbo["gdp"]
cbo['gfsrpn_cbo'] = (cbo["rev"] - cbo["outlays"]) / cbo["gdp"]

start = start.asfreq('Q') - 3
end = end.asfreq('Q')
end_long = end_long.asfreq("Q")

temp = longbase.loc[start:end, "xgdpn"]
temp = temp.groupby(temp.index.year).sum() 
temp.index = cbo.index
cbo["TPN_ts"] *= temp
cbo["TCIN_cs"] *= temp 
cbo["gfsrpn_cbo"] *= temp

TPN_fs = denton_boot(cbo["TPN_ts"].to_numpy())
TCIN_fs = denton_boot(cbo["TCIN_cs"].to_numpy())
gfsrpn_dent = denton_boot(cbo["gfsrpn_cbo"].to_numpy())

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")
longbase.loc[start-100:, 'dfpdbt'] = 0
longbase.loc[start-100:end, 'dfpex'] = 1
longbase.loc[start-100:end, 'dfpsrp'] = 0
longbase.loc[end+1:, 'dfpsrp'] = 1

longbase.loc[start:, "dmpintay"] = 1
longbase.loc[start:, "dmptay"] = 0
longbase.loc[start:, "dmpalt"] = 0
longbase.loc[start:, "dmpex"] = 0
longbase.loc[start:, "dmprr"] = 0
longbase.loc[start:, "dmptlr"] = 0
longbase.loc[start:, "dmptlur"] = 0
longbase.loc[start:, "dmptmax"] = 0
longbase.loc[start:, "dmptpi"] = 0
longbase.loc[start:, "dmptr"] = 0
longbase.loc[start:, "dmptrsh"] = 0

with_adds = frbus.init_trac(start, end, longbase)
with_adds.loc[start:end, "tpn_t"] = (TPN_fs + 
    with_adds.loc[start:end, "egsln"] + with_adds.loc[start:end, "egsen"] +
    TCIN_fs - with_adds.loc[start:end, "tcin"])
with_adds.loc[start:end, "tcin_t"] = TCIN_fs
with_adds.loc[start:end, "xgdpn_t"] = with_adds.loc[start:end, "xgdpn"]
with_adds.loc[start:end, "gfsrpn_t"] = gfsrpn_dent

print(with_adds.loc[start:end, ["tcin", "tcin_t", "tpn", "tpn_t"]])

out = frbus.mcontrol(start, end, with_adds, 
    targ=["tpn", "tcin", "xgdpn", "gfsrpn"], 
    traj=["tpn_t", "tcin_t", "xgdpn_t", "gfsrpn_t"], 
    inst=["trp_aerr", "trci_aerr", "xpn_aerr", "ugfsrp_aerr"])

out = out.filter(regex="^((?!_).)*$")

longbase.loc[start:end,:] = out.loc[start:end,:]
longbase = longbase.reset_index().rename(columns={"index":"obs"})
longbase.columns = [col.upper() for col in longbase.columns]

outpath = f"/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/Baselines/{stamp}"

if not os.path.exists(outpath):
    os.makedirs(outpath)

#longbase.to_csv(os.path.join(outpath, "LONGBASE.TXT"), index=False)

