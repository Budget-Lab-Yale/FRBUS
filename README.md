# FRBUS
This module provides helper functions for the Yale Budget Lab's use of FRB/US.

The code found here is written to be adaptable for whatever kind of policy scenario we may care to test. A general implementation of our dynamic revenue estimation script can be found in the Demos/ subdirectory. 

The Punchards/ subdirectory stores the runscripts (top level parameters) for each set of scenario tests.

Below, each sub library is briefly explained. An in depth analysis of our methodology, complete with formal mathematical explanations, can be found on our website.

COMPUTATION.py
    These functions perform mathematical operations necessary for our methodology. The majority of them are used to perform the special case of Denton's benchmarking method found in Boot, Feibes, and Lisman (1967).

PROCESSING.py
    These functions are straightforward, tidy wrappers for processing larger groups of data. For the most part, they apply the same mathematical operation repeatedly.

PUNCHCARD.py
    These functions integrate FRB/US runs with our data storage. For the most part, they read in data and do minor pre-processing before it is used in more complex operations. get_housing_subsidy_rates is an exception, as it performs a more complicated microdata calculation.

SIM_SETUP.py
    These functions do the FRB/US specific pre-processing steps and conduct the actual simulations. Such steps include setting policy levers, constructing the baseline values, calculating revenue paths, and performing dynamic revenue estimation.