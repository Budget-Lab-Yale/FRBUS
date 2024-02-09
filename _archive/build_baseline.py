import pandas
import datetime
import pyfrbus
import sys
import os

from pyfrbus.load_data import load_data
from pyfrbus.frbus import Frbus
from sim_setup import denton_boot
from punchcard import parse_tax_sim, read_macro

card_path = os.path.join(os.path.dirname(__file__), "..", "punchcards", "tcja_ext_build_card.csv")
card = pandas.read_csv(card_path)

run = 0

stamp = datetime.datetime.now().strftime('%Y%m%d%H') + "onecols"

longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS", str(card.loc[run, "lb_version"]), str(card.loc[run, "lb_vintage"]), "LONGBASE.TXT"))

ts = parse_tax_sim(card, run, True)
ts = ts[-31:]

start = pandas.Period("2023")
end = pandas.Period("2053")
end_long = end + 4*10

macro = read_macro(card.loc[run, "macro_path"])
macro = macro.loc[start:end]
macro['TPN_ts'] = ts["iit_etr"] / macro["gdp"]
macro['TCIN_cs'] = ts["revenues_corp_tax"] / macro["gdp"]
macro['gfsrpn_macro'] = (macro["rev"] - macro["outlays"]) / macro["gdp"]

start = start.asfreq('Q') - 3
end = end.asfreq('Q')
end_long = end_long.asfreq("Q")

temp = longbase.loc[start:end, "xgdpn"]
temp = temp.groupby(temp.index.year).sum() 
temp.index = macro.index
macro["TPN_ts"] *= temp
macro["TCIN_cs"] *= temp 
macro["gfsrpn_macro"] *= temp

TPN_fs = denton_boot(macro["TPN_ts"].to_numpy())
TCIN_fs = denton_boot(macro["TCIN_cs"].to_numpy())
gfsrpn_dent = denton_boot(macro["gfsrpn_macro"].to_numpy())

frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")
longbase.loc[:, 'dfpdbt'] = 1
longbase.loc[:, 'dfpex'] = 0
longbase.loc[:, 'dfpsrp'] = 0

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

#with_adds.loc[start:end, "tpn_t"] = (TPN_fs + 
#    with_adds.loc[start:end, "egsln"] + with_adds.loc[start:end, "egsen"] +
#    TCIN_fs - with_adds.loc[start:end, "tcin"])
with_adds.loc[start:end, "tpn_t"] = TPN_fs * 1.25
with_adds.loc[start:end, "tcin_t"] = with_adds.loc[start:end, "tcin"] #TCIN_fs
with_adds.loc[start:end, "xgdpn_t"] = with_adds.loc[start:end, "xgdpn"]
with_adds.loc[start:end, "gfsrpn_t"] = gfsrpn_dent
#with_adds.loc[start:, "gfdrt"] = max(with_adds.loc[start:end, "gfdbtn"] / with_adds.loc[start:end, "xgdpn"])
with_adds.loc[start:, "gfdrt"] = with_adds.loc[start,"gfdbtn"] / with_adds.loc[start,"xgdpn"]

out = frbus.mcontrol(start, end, with_adds, 
    targ=["tpn", "tcin", "xgdpn", "gfsrpn"], 
    traj=["tpn_t", "tcin_t", "xgdpn_t", "gfsrpn_t"], 
    inst=["trp_aerr", "trci_aerr", "xpn_aerr", "ugfsrp_aerr"])

print(with_adds.loc[start:end, ["tpn", "tpn_t"]])
print(out.loc[start:end, ["tpn", "tpn_t"]])

out = out.filter(regex="^((?!_).)*$")

longbase.loc[start:end,:] = out.loc[start:end,:]
longbase = longbase.reset_index().rename(columns={"index":"obs"})
longbase.columns = [col.upper() for col in longbase.columns]

outpath = f"/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/Baselines/{stamp}"

if not os.path.exists(outpath):
    os.makedirs(outpath)

longbase.to_csv(os.path.join(outpath, "LONGBASE.TXT"), index=False)

