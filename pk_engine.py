"""
One-compartment oral PK simulation engine.

Input:  dose (mg), cl_base (L/hr), vd (L), ka (1/hr), optional modifier functions
Output: (time_array, concentration_array) in hours and mg/L

Clearance is dynamic — it accepts Person 3's circadian_modifier and sleep_modifier
as scalar-returning callables: fn(t: float) -> float
"""

import numpy as np
from scipy.integrate import solve_ivp


def pk_simulate(
    dose: float,               # mg
    cl_base: float,            # L/hr — base (hepatic) clearance
    vd: float,                 # L  — volume of distribution
    ka: float,                 # 1/hr — first-order absorption rate
    t_end: float = 24.0,       # hr — simulation duration
    n_points: int = 500,
    circadian_modifier_fn=None,  # fn(t) -> float multiplier on CL
    sleep_modifier_fn=None,      # fn(t) -> float multiplier on CL
) -> tuple[np.ndarray, np.ndarray]:
    """
    Solve the one-compartment oral absorption model:
        dA_gut/dt = -ka * A_gut
        dC/dt     = (ka/Vd)*A_gut - (CL(t)/Vd)*C

    Returns (time_hr, concentration_mg_per_L).
    """

    def cl_dynamic(t: float) -> float:
        cl = cl_base
        if circadian_modifier_fn is not None:
            cl *= float(circadian_modifier_fn(t))
        if sleep_modifier_fn is not None:
            cl *= float(sleep_modifier_fn(t))
        return max(cl, 1e-3)  # floor prevents division by zero

    def odes(t, y):
        A_gut, C = y
        cl = cl_dynamic(t)
        dA_gut = -ka * A_gut
        dC = (ka / vd) * A_gut - (cl / vd) * C
        return [dA_gut, dC]

    t_eval = np.linspace(0, t_end, n_points)
    y0 = [dose, 0.0]  # all drug starts in gut compartment

    sol = solve_ivp(
        odes, (0, t_end), y0,
        t_eval=t_eval, method="RK45",
        rtol=1e-6, atol=1e-8,
    )

    if not sol.success:
        raise RuntimeError(f"ODE solver failed: {sol.message}")

    return sol.t, sol.y[1]  # time array, plasma concentration array


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    t, C = pk_simulate(
        dose=100,      # 100 mg
        cl_base=3.0,   # L/hr  (lamotrigine-like)
        vd=50.0,       # L
        ka=1.2,        # 1/hr
    )
    plt.figure(figsize=(8, 4))
    plt.plot(t, C, linewidth=2)
    plt.xlabel("Time (hr)")
    plt.ylabel("Plasma concentration (mg/L)")
    plt.title("One-compartment PK — baseline (no modifiers)")
    plt.tight_layout()
    plt.show()
