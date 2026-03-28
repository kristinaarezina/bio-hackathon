"""
Full drug pipeline — the single callable Person 4 uses.

Usage:
    from pipeline import run_drug_pipeline, DEMO_DRUGS
    result = run_drug_pipeline("midazolam", **DEMO_DRUGS["midazolam"])
    print(result["pk"]["concentration_mg_L"][:5])
"""

import json
from pathlib import Path

from pk_engine import pk_simulate
from person2_functions import predict_bbb
from person3_functions import circadian_modifier, sleep_modifier


# ---------------------------------------------------------------------------
# Drug parameters pulled from PK-DB / literature for the 3 demo drugs
# ---------------------------------------------------------------------------
DEMO_DRUGS: dict[str, dict] = {
    "lamotrigine": {
        "smiles": "Nc1cc(-c2ccccc2Cl)nc(N)n1",           # canonical
        "dose": 100.0,   # mg (typical maintenance dose)
        "cl_base": 1.65, # L/hr (low CL, renal + hepatic)
        "vd": 100.0,     # L
        "ka": 0.8,       # 1/hr
    },
    "simvastatin": {
        "smiles": "CCC(C)(C)C(=O)O[C@@H]1C[C@@H](C)C=C2C=C[C@H](C)[C@@H](CC[C@@H]3C[C@@H](O)CC(=O)O3)[C@@H]21",
        "dose": 40.0,    # mg
        "cl_base": 50.0, # L/hr (high first-pass; effective systemic CL is high)
        "vd": 500.0,     # L
        "ka": 0.9,       # 1/hr
    },
    "midazolam": {
        "smiles": "CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21",
        "dose": 5.0,     # mg (IV/oral sedation dose)
        "cl_base": 27.0, # L/hr (high hepatic CL via CYP3A4)
        "vd": 50.0,      # L
        "ka": 2.5,       # 1/hr (fast absorption)
    },
}


def run_drug_pipeline(
    drug_name: str,
    smiles: str,
    dose: float,
    cl_base: float,
    vd: float,
    ka: float,
    t_end: float = 24.0,
    apply_modifiers: bool = True,
) -> dict:
    """
    Full pipeline: SMILES → BBB prediction → PK simulation with circadian/sleep modifiers.

    Args:
        drug_name:        human-readable name
        smiles:           canonical SMILES string
        dose:             dose in mg
        cl_base:          base clearance in L/hr
        vd:               volume of distribution in L
        ka:               absorption rate constant in 1/hr
        t_end:            simulation end time in hours (default 24)
        apply_modifiers:  set False to run baseline PK without circadian/sleep

    Returns dict with keys: drug, smiles, bbb_penetrant, bbb_probability, pk
    """

    # Step 1 — BBB classification (Person 2)
    bbb = predict_bbb(smiles)

    # Step 2 — PK simulation with dynamic clearance (Person 3)
    circ_fn = circadian_modifier if apply_modifiers else None
    sleep_fn = sleep_modifier if apply_modifiers else None

    time_arr, conc_arr = pk_simulate(
        dose=dose,
        cl_base=cl_base,
        vd=vd,
        ka=ka,
        t_end=t_end,
        circadian_modifier_fn=circ_fn,
        sleep_modifier_fn=sleep_fn,
    )

    # Step 3 — Derived PK metrics
    t_max_idx = int(conc_arr.argmax())
    c_max = float(conc_arr[t_max_idx])
    t_max = float(time_arr[t_max_idx])
    auc = float(time_arr[-1] - time_arr[0]) * float(conc_arr.mean())  # trapezoidal approx

    return {
        "drug": drug_name,
        "smiles": smiles,
        "bbb_penetrant": bool(bbb["label"]),
        "bbb_probability": bbb["probability"],
        "pk": {
            "dose_mg": dose,
            "cl_base_L_hr": cl_base,
            "vd_L": vd,
            "ka_1_per_hr": ka,
            "c_max_mg_L": round(c_max, 4),
            "t_max_hr": round(t_max, 2),
            "auc_mg_hr_L": round(auc, 4),
            "modifiers_applied": apply_modifiers,
            "time_hr": [round(x, 4) for x in time_arr.tolist()],
            "concentration_mg_L": [round(x, 6) for x in conc_arr.tolist()],
        },
    }


def run_all_demo_drugs(save: bool = True) -> dict[str, dict]:
    results = {}
    for name, params in DEMO_DRUGS.items():
        print(f"Running pipeline for {name}...")
        results[name] = run_drug_pipeline(drug_name=name, **params)
        pk = results[name]["pk"]
        print(f"  Cmax={pk['c_max_mg_L']} mg/L at t={pk['t_max_hr']} hr")
        print(f"  BBB={'yes' if results[name]['bbb_penetrant'] else 'no'} "
              f"(p={results[name]['bbb_probability']})")

    if save:
        out = Path(__file__).parent / "data" / "pipeline_results.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(results, indent=2))
        print(f"\nSaved results to {out}")

    return results


if __name__ == "__main__":
    run_all_demo_drugs()
