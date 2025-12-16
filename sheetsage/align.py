import numpy as np
from scipy.interpolate import interp1d


def _extrapolating_linear_interp1d(a, b, safe=True):
    """
    Creates an extrapolating linear interpolation function.

    Args:
        a (list or np.ndarray): The x-coordinates of the data points.
        b (list or np.ndarray): The y-coordinates of the data points.
        safe (bool): If True, performs validation checks on input data.

    Returns:
        scipy.interpolate.interp1d: An interpolation function that extrapolates linearly.

    Raises:
        ValueError: If input validation fails when safe is True.
    """
    if safe:
        if isinstance(a, np.ndarray):
            a = a.tolist()
        if isinstance(b, np.ndarray):
            b = b.tolist()
        if a != sorted(a):
            raise ValueError()
        if b != sorted(b):
            raise ValueError()
        if len(a) != len(b):
            raise ValueError()
        if len(np.unique(a)) != len(a):
            raise ValueError()
        if len(np.unique(b)) != len(b):
            raise ValueError()
    return interp1d(a, b, kind="linear", fill_value="extrapolate")


def create_beat_to_time_fn(beats, times, safe=True):
    """
    Creates a function that maps beat indices to timestamps.

    Args:
        beats (list or np.ndarray): List of beat indices.
        times (list or np.ndarray): List of corresponding timestamps.
        safe (bool): If True, performs validation checks on input data.

    Returns:
        scipy.interpolate.interp1d: A function taking beat indices and returning timestamps.
    """
    return _extrapolating_linear_interp1d(beats, times, safe=safe)


def create_time_to_beat_fn(beats, times, safe=True):
    """
    Creates a function that maps timestamps to beat indices.

    Args:
        beats (list or np.ndarray): List of beat indices.
        times (list or np.ndarray): List of corresponding timestamps.
        safe (bool): If True, performs validation checks on input data.

    Returns:
        scipy.interpolate.interp1d: A function taking timestamps and returning beat indices.
    """
    return _extrapolating_linear_interp1d(times, beats, safe=safe)
