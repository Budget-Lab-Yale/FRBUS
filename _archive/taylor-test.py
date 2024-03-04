import pandas

from pyfrbus.frbus import Frbus
from pyfrbus.sim_lib import sim_plot
from pyfrbus.load_data import load_data


# Load data
data = load_data("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS/v1/20240104/LONGBASE.TXT")

# Load model
frbus = Frbus("/gpfs/gibbs/project/sarin/lj446/model.xml")

# Specify dates
start = pandas.Period("YOUR START DATE")
end = pandas.Period("YOUR END DATE")

# Standard configuration, use surplus ratio targeting
data.loc[start:end, "dfpdbt"] = 0
data.loc[start:end, "dfpsrp"] = 1
data.loc[start:end, "dmptay"] = 1

# Solve to baseline with adds
with_adds = frbus.init_trac(start, end, data)

# 100 bp monetary policy shock and solve
with_adds.loc[start, "rfftay_aerr"] += "YOUR NEW TERM AND ITS COEFFICIENT"
sim = frbus.solve(start, end, with_adds)

# View results
sim_plot(with_adds, sim, start, end)