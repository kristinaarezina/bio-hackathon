"""
STUB — Person 3's circadian and sleep modifier functions.

Replace this file entirely when Person 3 delivers their model.
The pipeline (pipeline.py) and pk_engine.py call:
    circadian_modifier(t: float) -> float
    sleep_modifier(t: float) -> float

Both functions receive t in hours (0–24 range, can exceed 24 for multi-day).
Both return a scalar multiplier applied to base clearance.

Biological meaning:
  circadian_modifier: ~±30% oscillation reflecting CYP3A4/CYP2D6 circadian expression
  sleep_modifier:     ~30% reduction in hepatic clearance during sleep (23:00–07:00)
"""

import math


def circadian_modifier(t: float) -> float:
    """
    Stub: cosine oscillation peaking at ~14:00 (t=14 if dose at midnight).
    Amplitude ±0.3 around 1.0.
    """
    return 1.0 + 0.3 * math.cos(2 * math.pi * (t - 14) / 24)


def sleep_modifier(t: float) -> float:
    """
    Stub: 30% CL reduction during sleep window (23:00–07:00).
    """
    hour = t % 24
    if hour >= 23 or hour < 7:
        return 0.7
    return 1.0
