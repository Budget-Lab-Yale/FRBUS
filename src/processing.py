import pandas
import numpy
import os

from pandas import DataFrame, Period, PeriodIndex
from pyfrbus.load_data import load_data

from sim_setup import denton_boot
from punchcard import parse_tax_sim, read_macro

def dentonizer(data: DataFrame):
    #---------------------------------------------------------------------
    # This function applies the quarterly interpolation method to an entire
    #    dataframe (or subset of a dataframe) of annual data.
    # Parameters:
    #   data (DataFrame): Annual data.
    # Returns:
    #   out (DataFrame): The same data as smooth quarters.
    #---------------------------------------------------------------------
    out = pandas.DataFrame()

    for col in data.columns:
        out.loc[:, col] = denton_boot(data.loc[:,col].to_numpy())

    out.index = pandas.period_range(start=str(data.index[0])+"Q1", end = str(data.index[len(data)-1])+"Q4", freq="Q")

    return(out)

def calc_delta(base: DataFrame, sim: DataFrame):
    #---------------------------------------------------------------------
    # This function takes two DataFrames of the same variables and calculates
    #    the difference between the two. Typically used for dynamic revenue.
    # Parameters:
    #   base (DataFrame): Baseline run
    #   sim  (DataFrame): Scenario run  
    # Returns:
    #   delta (DataFrame): Differences between base and scenario runs.
    #---------------------------------------------------------------------
    delta = pandas.DataFrame()

    for col in base.columns:
        delta.loc[:, col] = sim.loc[:, col] - base.loc[:, col]
    
    return(delta)

def process_dynamic_rev_delta(card: DataFrame, run: int, stamp: str, outpath = None):

    start = pandas.Period(card.loc[run, "start"], freq="Q")
    end   = pandas.Period(card.loc[run, "end"], freq="Q")
    frbd = DataFrame()
    

    # Aggregating income variables and deflating
    df1 = rev_delta_helper(card, run, start, end, stamp)
    df2 = rev_delta_helper(card, 0, start, end, stamp)
    frbd['pct_chg_real_income'] = df1.real_income / df2.real_income -1

    start = start.asfreq('Y')
    end = end.asfreq('Y')
    macro = read_macro(card.loc[run, "macro_path"]).loc[start:end, :]

    # Bringing in baseline revenue series and aggregating
    df3 = parse_tax_sim(card, 0, base = True).loc[start:end, :].drop('iit_etr', axis=1)
    df3['outlays_tax_credits'] *= -1
    df3['summed'] = df3.sum(axis=1)

    # Bringing in scenario revenue series and aggregating
    df4 = parse_tax_sim(card, run).loc[start:end, :]
    df4 = df4[df4.columns.drop(list(df4.filter(regex='base|jct|iit_etr')))]
    df4['outlays_tax_credits'] *= -1
    df4['summed'] = df4.loc[start:, :].sum(axis=1)    

    # Calculating conventional revenue delta and corresponding metrics
    conv_est = DataFrame()
    conv_est['nominal'] = df4.summed - df3.summed
    conv_est['share_gdp'] = conv_est.nominal / macro.gdp_fy
    conv_est['real'] = conv_est.nominal / df2.pgdp

    # Calclutaing baseline revenue series
    base_rev = DataFrame()
    base_rev['nominal'] = df3.summed + macro.loc[:, ["rev_excise", "rev_customs", "rev_misc"]].sum(axis=1)
    base_rev['share_gdp'] = base_rev.nominal / macro.gdp_fy
    base_rev['real'] = base_rev.nominal / df2.pgdp

    # Real dynamic revenue series, including delta
    real_dy_rev = DataFrame()
    real_dy_rev['dynamic_delta'] = frbd.pct_chg_real_income * (base_rev.real + conv_est.real)
    real_dy_rev['level'] = base_rev.real + conv_est.real + real_dy_rev.dynamic_delta
    real_dy_rev['dynamic_ratio'] = (real_dy_rev.dynamic_delta + conv_est.real) / conv_est.real
    real_dy_rev['dynamic_delta'] *= df2.pgdp
    real_dy_rev['decade'] = numpy.select(
        [
            real_dy_rev.index.year < start.year + 10, 
            real_dy_rev.index.year < start.year + 20,
            real_dy_rev.index.year < start.year + 30
        ],
        [
            'Budget Window',
            'Second Decade',
            'Third Decade'
        ],
        default=None
    )

    if outpath is not None:
        real_dy_rev.to_csv(os.path.join(outpath, 'real_dynamic_revenue_delta.csv'))
    return()
    
 

def rev_delta_helper(card: DataFrame, run: int, start: Period, end: Period, stamp: str):

    longbase = load_data(os.path.join("/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/tcja_ext", stamp, str(card.loc[run, "ID"]),str(card.loc[run, "ID"])+"_LONGBASE.csv"))

    data = DataFrame()
    temp = longbase.loc[start:end, ["ynicpn", "yniln", "ynirn"]].sum(axis=1)
    data["income"] = temp.groupby(temp.index.year).mean()
    data["pgdp"] = longbase.loc[start:end, "pgdp"].groupby(temp.index.year).mean()
    data.index = PeriodIndex(data.index, freq='Y')

    data["pgdp"] /= data.loc[start.asfreq('Y'), "pgdp"]
    data["real_income"] = data["income"] / data["pgdp"]

    return(data.loc[:, ["real_income", "pgdp"]])


