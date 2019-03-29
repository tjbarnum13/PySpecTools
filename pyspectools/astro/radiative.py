
""" radiative.py

    Routines for calculating quantities useful for
    radiative transfer, such as Einstein coefficients
"""
import numpy as np
import pandas as pd
from scipy import constants

from pyspectools.units import kbcm, MHz2cm


def parse_str(filepath):
    # Function that will parse a .str file from SPCAT
    # This file can be generated by supplying 0020 as
    # the first flag in the `.int` file.
    # Returns a Pandas dataframe
    names = [
        "Frequency",
        "RTDM",
        "Formatting",
        "Upper QN",
        "Lower QN",
        "Dipole Category"
        ]
    # Use fixed-width reading in pandas
    str_df = pd.read_fwf(
        filepath,
        widths=[15, 15, 5, 12, 12, 11],
        names=names,
        index=False
    )
    return str_df


def I2S(I, Q, frequency, E_lower, T=300.):
    """
    Function for converting intensity (in nm^2 MHz) to the more standard intrinsic linestrength, S_ij mu^2.

    Parameters
    ----------
    I - float
        The log of the transition intensity, typically given in catalog files
    Q - float
        Partition function at specified temperature T
    frequency - float
        Frequency of the transition in MHz
    E_lower - float
        ENergy of the lower state in wavenumbers
    T - float
        Temperature in Kelvin

    Returns
    -------
    siju - float
        Value of the intrinsic linestrength
    """
    E_upper = calc_E_upper(frequency, E_lower)
    # top part of the equation
    A = 10.**I * Q
    lower_factor = boltzmann_factor(E_lower, T)       # Boltzmann factors
    upper_factor = boltzmann_factor(E_upper, T)
    # Calculate the lower part of the equation
    # The prefactor included here is taken from Brian
    # Drouin's notes
    B = (4.16231e-5 * frequency * (lower_factor - upper_factor))
    return A / B


def calc_E_upper(frequency, E_lower):
    """
    Calculate the upper state energy, for a given lower state energy and the frequency of the transition.

    Parameters
    ----------
    frequency - float
        Frequency of the transition in MHz
    E_lower - float
        Lower state energy in wavenumbers

    Returns
    -------
    E_upper - float
        Upper state energy in wavenumbers
    """
    transition_freq = MHz2cm(frequency)
    return transition_freq + E_lower


def boltzmann_factor(E, T):
    """
    Calculate the Boltzmann weighting for a given state and temperature.

    Parameters
    ----------
    E - float
        State energy in wavenumbers
    T - float
        Temperature in Kelvin

    Returns
    -------
    boltzmann_factor - float
        Unitless Boltzmann factor for the state
    """
    return np.exp(-E / (kbcm * T))


def approx_Q_linear(B, T):
    """
    Approximate rotational partition function for a linear molecule.

    Parameters
    ----------
    B - float
        Rotational constant in MHz.
    T - float
        Temperature in Kelvin.

    Returns
    -------
    Q - float
        Rotational partition function at temperature T.
    """
    Q = 2.0837e4 * (T / B)
    return Q


def approx_Q_top(A, B, T, sigma=1, C=None):
    """
    Approximate expression for the (a)symmetric top partition function. The expression is adapted from Gordy and Cook,
    p.g. 57 equation 3.68. By default, the prolate top is used if the C constant is not specified, where B = C.
    Oblate case can also be specified if A = C.

    Parameters
    ----------
    A - float
        Rotational constant for the A principal axis, in MHz.
    B - float
        Rotational constant for the B principal axis, in MHz.
    T - float
        Temperature in Kelvin
    sigma - int
        Rotational level degeneracy; i.e. spin statistics
    C - float, optional
        Rotational constant for the C principal axis, in MHz. Defaults to None, which will reduce to the prolate
        top case.

    Returns
    -------
    Q - float
        Partition function for the molecule at temperature T
    """
    if C is None:
        # For a symmetric top, B = C
        C = B
    Q = (5.34e6 / sigma) * (T**3. / (A * B * C))**0.5
    return Q


def einsteinA(S, frequency):
    # Prefactor is given in the PGopher Intensity formulae
    # http://pgopher.chm.bris.ac.uk/Help/intensityformulae.htm
    # Units of the prefactor are s^-1 MHz^-3 D^-2
    # Units of Einstein A coefficient should be in s^-1
    prefactor = 1.163965505e-20
    return prefactor * frequency**3. * S


def calc_einstein(str_filepath):
    """ High-level function for calculating Einstein A
        coefficients for a given .str file output from
        SPCAT.
    """
    str_df = parse_str(str_filepath)
    # Calculate the transition moment dipole from the
    # square of the str output
    str_df["TDM"] = str_df["RTDM"]**2.
    # Calculate the Einstein A coefficients in units
    # of per second
    str_df["Einstein A"] = einsteinA(
        str_df["TDM"],
        str_df["Frequency"]
        )
    # Sort the dataframe by ascending frequency
    str_df = str_df.sort_values(["Frequency"], ascending=True)
    return str_df
