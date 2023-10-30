import pandas
import numpy

from pyfrbus.frbus import Frbus
from pyfrbus.sim_lib import sim_plot
from pyfrbus.load_data import load_data

########################## STEP 0: Filepaths and parameters ##########################

# Load data
data = load_data("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS/v1/20171220/LONGBASE.TXT")

# Load model
frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")

# Load changes in tax rates and transfers
tax_delta = load_data("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/001_POLICY_SHOCKS.TXT")

# Specify dates: using 50/125 years for now
start = pandas.Period("2017Q3")
end_short = start + 200
end_long = start + 500


########################## STEP 1: Running Baseline 2017 FBRUS ##########################
# Initialize FRBUS to get baseline input file
input_baseline = frbus.init_trac(start, end_long, data)

# FISCAL POLICY LEVERS
# Exogenous fiscal policy until end_short, then surplus ratio targeting
input_baseline.loc[start-100:end_long+100, 'dfpdbt'] = 0
input_baseline.loc[start-100:end_short, 'dfpex'] = 1
input_baseline.loc[end_short+1:end_long+100, 'dfpsrp'] = 1

# MONETARY POLICY LEVERS
# Inertial Taylor rule
input_baseline.loc[start-100:end_long+100, 'dmpalt'] = 0
input_baseline.loc[start-100:end_long+100, 'dmpex'] = 0
input_baseline.loc[start-100:end_long+100, 'dmpintay'] = 1
input_baseline.loc[start-100:end_long+100, 'dmprr'] = 0
input_baseline.loc[start-100:end_long+100, 'dmptay'] = 0
input_baseline.loc[start-100:end_long+100, 'dmptlr'] = 0
input_baseline.loc[start-100:end_long+100, 'dmptlur'] = 0
input_baseline.loc[start-100:end_long+100, 'dmptmax'] = 0
input_baseline.loc[start-100:end_long+100, 'dmptlr'] = 0
input_baseline.loc[start-100:end_long+100, 'dmptpi'] = 0
input_baseline.loc[start-100:end_long+100, 'dmptr'] = 0
input_baseline.loc[start-100:end_long+100, 'dmptrsh'] = 0
input_baseline.to_csv("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/input_baseline.csv")

# Simulate baseline
sim_baseline = frbus.solve(start, end_long, input_baseline)

# Save entire results into CSV
sim_baseline.to_csv("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/sim_baseline.csv")

#######################################################################################

###################### STEP 2: FRBUS Conventional Revenue Estimate ######################
# Corporate tax increases in revenue : d_TRCI * YNICPN
sim_baseline['corp_rev_delta']= sim_baseline['ynicpn']*tax_delta['d_trci']

# Personal tax increases in revenue : d_TRP * (YPN - GTN)
sim_baseline['pers_rev_delta']= (sim_baseline['ypn'] - sim_baseline['gtn'])*tax_delta['d_trp']

# Government transfers : d_GTN
sim_baseline['transfers_delta']= tax_delta['d_gtn']

# Sum change in transfers, corp and pers revenue 
sim_baseline['conventional_rev_est'] =      sim_baseline['transfers_delta'] + sim_baseline['corp_rev_delta'] + \
                                                sim_baseline['pers_rev_delta']

# Save entire results into CSV
conventional_rev = sim_baseline[['corp_rev_delta', 'pers_rev_delta', 'transfers_delta', 'conventional_rev_est']]
conventional_rev.to_csv("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/conventional_rev.csv")

#######################################################################################

########################## STEP 3: FRBUS Dynamic Revenue Estimate #####################
# Initialize input file for dynamic estimate
input_scenario = input_baseline

### Add shocks to _aerr variables from initialized FRBUS model ###
# Marginal rates are exogenous so there is no *_aerr variable
input_scenario.loc[start:end_short, 'trfcim']     += tax_delta.loc[start:end_short, 'd_trfcim']
input_scenario.loc[start:end_short, 'trfpm']      += tax_delta.loc[start:end_short, 'd_trfpm']

# Average rates are endogenous so we can use the *_aerr
input_scenario.loc[start:end_short, 'trci_aerr']  += tax_delta.loc[start:end_short, 'd_trci']
input_scenario.loc[start:end_short, 'trp_aerr']   += tax_delta.loc[start:end_short, 'd_trp']

# Government transfers 
input_scenario.loc[start:end_short, 'gtn_aerr']   += tax_delta.loc[start:end_short, 'd_gtn']

## Solve model
sim_scenario = frbus.solve(start, end_long, input_scenario)

# Save entire results into CSV
sim_scenario.to_csv("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/sim_scenario.csv")

## Generate dynamic revenue estimates and save to CSV
# Corporate tax increases in revenue 
sim_scenario['corp_rev_delta']= sim_scenario['tcin'] - sim_baseline['tcin']

## Personal tax increases in revenue 
sim_scenario['pers_rev_delta']= sim_scenario['tpn'] - sim_baseline['tpn']

# Government transfers
sim_scenario['transfers_delta']= sim_scenario['gtn'] - sim_baseline['gtn']

#Overall change in government deficit
sim_scenario['dynamic_rev_est']= sim_scenario['gfsrpn'] - sim_baseline['gfsrpn']

dynamic_rev = sim_scenario[['corp_rev_delta','pers_rev_delta','transfers_delta','dynamic_rev_est']]
dynamic_rev.to_csv("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja-2017/dynamic_rev.csv")