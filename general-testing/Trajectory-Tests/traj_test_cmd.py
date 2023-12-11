import pandas
import numpy
import time
import matplotlib.pyplot as plt
import logging
import os
import sys

from pyfrbus.frbus import Frbus
from pyfrbus.sim_lib import sim_plot
from pyfrbus.load_data import load_data

########################### STEP 0: Filepaths and parameters ##########################

y = int(sys.argv[1])
j = int(sys.argv[2])
i = int(sys.argv[3])
count = int(sys.argv[4])


# Load data - using current longbase 
data = load_data("/gpfs/gibbs/project/sarin/shared/raw_data/FRBUS/v1/20230927/LONGBASE.TXT")

# Load model
frbus = Frbus("/gpfs/gibbs/project/sarin/shared/conda_pkgs/pyfrbus/models/model.xml", mce="mcap+wp")


# Specify dates: using 30/40 years for now
start = pandas.Period("2023Q3")
end_short = start + 120
end_long = start + 120 + 4*y

delta_pers = i*0.01
delta_corp = j*0.01
########################### STEP 1: Specify fiscal/monetary policy levers ##########################

input_baseline = frbus.init_trac(start, end_long, data)


# FISCAL POLICY LEVERS
# Exogenous fiscal policy until end_short, then surplus ratio targeting
input_baseline.loc[start-100:end_long+100, 'dfpsrp'] = 0
input_baseline.loc[start-100:end_short, 'dfpex'] = 1
input_baseline.loc[start-100:end_short, 'dfpdbt'] = 0
input_baseline.loc[end_short+1:end_long+100, 'dfpdbt'] = 1

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



########################### STEP 2: Specify trajectory variables ##########################

try:
        sim_baseline = frbus.solve(start, end_long, input_baseline)
except Exception as e:
        run = f"{count}, {end_long},{-1*delta_pers},{-1*delta_corp},-1,0,0 \n"
        error_message = f"Run {count} failed while constructing sim baseline with the following error: \n         {e} \n"
        #logging.error(error_message)
        with open('outcome_vars.csv', 'a') as f:
                f.write(run)
        with open('error_log.txt', 'a') as l:
                l.write(error_message)

########################### STEP 3: Specify trajectory variables ########################## 
else:
        # First hold average corporate/personal tax rates to their 2023Q3 level 
        sim_baseline.loc[start-100:end_long+100, "trp_t"] = numpy.nan
        sim_baseline.loc[start+1:end_short, "trp_t"] =  sim_baseline.loc[start, "trp"] - delta_pers

        sim_baseline.loc[start-100:end_long+100, "trci_t"] = numpy.nan
        sim_baseline.loc[start+1:end_short, "trci_t"] = sim_baseline.loc[start, "trci"] - delta_corp

        # Run mcontrol
        targ = ["trp", "trci"]
        traj = ["trp_t", "trci_t"]
        inst = ["trp_aerr", "trci_aerr"]

        try:
                start_time = time.time() # For computing run time
                sim_baseline_m = frbus.mcontrol(start, end_long, sim_baseline, targ, traj, inst)

        except Exception as e:
                run = f"{count}, {end_long},{-1*delta_pers},{-1*delta_corp},-1,0,0 \n"
                error_message = f"Run {count} with parameters End Long: {end_long}, Delta Personal: {delta_pers}, Delta Corp: {delta_corp}, failed with the following error: \n         {e} \n"
                #logging.error(error_message)
                with open('outcome_vars.csv', 'a') as f:
                        f.write(run)
                with open('error_log.txt', 'a') as l:
                        l.write(error_message)
        else:
                end_time = time.time()  # Record the end time
                runtime = end_time - start_time
                last_surp = sim_baseline_m.loc[end_short, "gfsrpn"]

                run = f"{count}, {end_long},{-1*delta_pers},{-1*delta_corp},1,{runtime},{last_surp} \n"
                with open('outcome_vars.csv', 'a') as f:
                        f.write(run)
                        

