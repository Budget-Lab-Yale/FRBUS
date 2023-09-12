import pandas
import datetime

from punchcard import ybl_Frbus, ybl_load_data
from pyfrbus.frbus import init_trac
from sim_setup import levers

data_root = "/gpfs/gibbs/project/sarin/shared"

#can move into loop if we want a vintage stamp for every model run
ct = datetime.datetime.now()
stamp = str(ct.year)+str(ct.month)+str(ct.day)+str(ct.hour)

card = pandas.read_csv(sys.argv[1])

for run in range(card.shape[0]):

    data = ybl_load_data(card.loc[run, "version"], card.loc[run, "vintage"])

    frbus = ybl_Frbus(card.loc[run, "version"], card.loc[run, "vintage"])

    start = pandas.Period(card.loc[run, "start"])
    end = pandas.Period(card.loc[run, "end"])

    levers(card, start, end, data, run)

    with_adds = frbus.init_trac(start, end, data)

    
    #run_out()