import numpy as np
from numpy import array

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
    pattern = np.array([1,1,1,1])
    return(np.kron(np.eye(T), pattern))

def calc_c(Tq: int):
    #---------------------------------------------------------------------
    # This function creates a square band matrix for Denton interpolation
    # Parameters:
    #   Tq (int) : The number of quarters to be interpolated
    # Returns:
    #   C (numpy): A Tq X Tq band matrix
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
    # Thank you: http://scipy-lectures.org/advanced/advanced_numpy/#indexing-scheme-strides
    a = np.asarray(a)
    p = np.zeros(W-1,dtype=a.dtype)
    b = np.concatenate((p,a,p))
    s = b.strides[0]
    strided = np.lib.stride_tricks.as_strided
    return strided(b[W-1:], shape=(W,len(a)+W-1), strides=(-s,s))

