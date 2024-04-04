import numpy as np
import pandas

from numpy import array
from pandas import DataFrame, Period, PeriodIndex

def denton_boot(Annual: array):
    #---------------------------------------------------------------------
    # This function takes in annual tax revenue data and interpolates it 
    # to quarterly frequency. This method smooths the new year step up.
    # Parameters:
    #   Annual (array): Annual tax revenue data of length T
    # Returns:
    #   out (array): Quarterly tax revenue data of length 4T
    #---------------------------------------------------------------------
    T = len(Annual)
    Tq = T * 4

    C = calc_c(Tq)
    J = calc_j(T)
    J_t = np.transpose(J * -1)
    zero4 = np.zeros((T,T))
    
    lhs1 = np.concatenate((C, J), axis=0)
    lhs2 = np.concatenate((J_t, zero4), axis=0)
    lhs = np.linalg.inv(np.concatenate((lhs1, lhs2), axis=1))   
    rhs = np.append(np.zeros(Tq), Annual)

    out = np.dot(lhs, rhs)
    return(out[0:Tq])

def calc_j(T: int):
    #---------------------------------------------------------------------
    # This function creates a Kronecker pattern matrix of 1s:
    # 1,1,1,1,0,0,0,0,...0,0,0,0
    # 0,0,0,0,1,1,1,1,...0,0,0,0
    # ..........................
    # ..........................
    # ..........................
    # 0,0,0,0,0,0,0,0,...1,1,1,1
    # Parameters:
    #   T    (int) : Number of years in the data.
    # Returns:
    #   Val (array): A Kronecker matrix of 1s.
    #---------------------------------------------------------------------
    pattern = np.array([1,1,1,1])
    return(np.kron(np.eye(T), pattern))

def calc_c(Tq: int):
    #---------------------------------------------------------------------
    # This function creates a square band matrix for Denton interpolation
    # Parameters:
    #   Tq (int) : The number of quarters to be interpolated
    # Returns:
    #   C (array): A Tq X Tq band matrix
    #---------------------------------------------------------------------
    base = inner_band([2,-8,12,-8,2], Tq-4)
    v0 = np.zeros(Tq)
    v1 = np.zeros(Tq)
    np.put(v0, [0,1,2], [2,-4,2])
    np.put(v1, [0,1,2,3], [-4,10,-8,2])
    out = np.insert(base, 0, v1, axis=0)
    out = np.insert(out, 0, v0, axis=0)
    out = np.insert(out, len(out), np.flip(v1), axis=0)
    out = np.insert(out, len(out), np.flip(v0), axis=0)
    return(out)

def inner_band(a, W):
    #---------------------------------------------------------------------
    # This function creates the inner, repeating Kronecker style portion 
    #    of the square matrix.
    # Parameters:
    #   a  (int)   : Vector of the pattern to fill the band matrix
    #   W  (int)   : Number of quarters minus 1 year 
    # Returns:
    #   Val (array): Repeated pattern matrix.
    #
    # Thank you: http://scipy-lectures.org/advanced/advanced_numpy/#indexing-scheme-strides
    #---------------------------------------------------------------------
    a = np.asarray(a)
    p = np.zeros(W-1,dtype=a.dtype)
    b = np.concatenate((p,a,p))
    s = b.strides[0]
    strided = np.lib.stride_tricks.as_strided
    return strided(b[W-1:], shape=(W,len(a)+W-1), strides=(-s,s))

def smooth_path(base: DataFrame, scen: DataFrame):
    #---------------------------------------------------------------------
    # This function creates a vector of values weighted between the baseline
    #   and scenario paths of a variable so that it starts as the baseline 
    #   value and ends at the scenario.
    # Parameters:
    #   base        (int) : baseline values of a variable
    #   scen        (int) : scenario values for a variable.
    # Returns:
    #   out (Vector[int]) : A vector of weighted values between two vectors.
    #---------------------------------------------------------------------
    weights_base = np.linspace(start = 0, stop = 1, num = len(base))
    weights_scen = np.flip(weights_base)
    out = (base * weights_base) + (scen * weights_scen)

    return(out)

