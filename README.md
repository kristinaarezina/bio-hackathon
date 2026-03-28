# Bio Hackathon — Personalized Drug PK Simulator

Simulates how a drug moves through an individual's body over time, accounting for blood-brain barrier penetration, CYP450 metabolism, and person-specific circadian and sleep patterns. Built in one day across four roles.

---

## What this repo does

Takes a drug (SMILES + dose + PK parameters), runs it through a one-compartment pharmacokinetic model, and outputs a plasma concentration curve that reflects:

- Whether the drug crosses the blood-brain barrier (BBB classifier)
- How circadian rhythm and sleep state modulate hepatic clearance in real time
- Literature-backed PK parameters for three demo drugs (lamotrigine, simvastatin, midazolam)

The result is a time-series of plasma concentration (mg/L) plus derived metrics (Cmax, Tmax, AUC) that downstream visualization or dosing logic can consume.

---

## Team roles

| Person | Role | Deliverable |
|--------|------|-------------|
| Kristina| Data eng | Data pipeline + PK engine (this repo) |
| Karthik MK | ML | BBB classifier → `person2_functions.py` |
| Alejandro| Bio/math | Circadian + sleep modifiers → `person3_functions.py` |
|ah-gilani | Frontend/viz | Calls `pipeline.py`, renders concentration curves |

---

## Files

```
bio_hackathon/
├── smiles.py              # Pull canonical SMILES for 3 drugs from PubChem
├── query_PK-DB.py         # Query PK-DB for CL, t½, Vd for 3 drugs
├── CYP450_dataset.py      # Download CYP450 inhibition dataset from PubChem bioassays
├── pk_engine.py           # One-compartment PK ODE solver (the math core)
├── pipeline.py            # Full callable pipeline — Person 4's entry point
├── person2_functions.py   # Stub for BBB classifier (replace when Person 2 delivers)
├── person3_functions.py   # Stub for circadian/sleep modifiers (replace when Person 3 delivers)
├── B3DB/                  # Blood-brain barrier dataset (cloned from theochem/B3DB)
└── data/                  # Generated outputs
    ├── drug_smiles.json
    ├── pkdb_results.json
    ├── cyp450_clean.parquet
    └── pipeline_results.json
```

---

## Demo drugs and PK parameters

| Drug | Indication | CL (L/hr) | Vd (L) | ka (1/hr) | Notes |
|------|-----------|-----------|--------|-----------|-------|
| Lamotrigine | Epilepsy / bipolar | 1.65 | 100 | 0.8 | Low CL, renal + hepatic |
| Simvastatin | Hypercholesterolemia | 50 | 500 | 0.9 | High first-pass via CYP3A4 |
| Midazolam | Sedation / anesthesia | 27 | 50 | 2.5 | High CL, fast absorption, CYP3A4 probe |

---

## PK model

One-compartment oral absorption:

```
dA_gut/dt = -ka × A_gut
dC/dt     = (ka/Vd) × A_gut  −  (CL(t)/Vd) × C
```

`CL(t)` is dynamic — it multiplies base clearance by Person 3's circadian and sleep modifier functions at each time step, solved with `scipy.integrate.solve_ivp` (RK45).

---

## Quickstart

```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Pull SMILES for the 3 demo drugs
python smiles.py

# 3. Query PK-DB for literature PK values
python query_PK-DB.py

# 4. Download CYP450 inhibition dataset (takes a few minutes — caches locally)
python CYP450_dataset.py --fast   # labels only, no SMILES fetch (faster)

# 5. Run the full pipeline end-to-end
python pipeline.py
```

Output goes to `data/pipeline_results.json`.

---

## Integration interface for Person 4

```python
from pipeline import run_drug_pipeline, DEMO_DRUGS

result = run_drug_pipeline("midazolam", **DEMO_DRUGS["midazolam"])

result["bbb_penetrant"]                    # bool
result["bbb_probability"]                  # float
result["pk"]["time_hr"]                    # list of 500 time points
result["pk"]["concentration_mg_L"]         # matching concentration values
result["pk"]["c_max_mg_L"]                 # peak concentration
result["pk"]["t_max_hr"]                   # time of peak
result["pk"]["auc_mg_hr_L"]               # area under the curve
```

Set `apply_modifiers=False` to get the flat baseline curve without circadian/sleep effects.

---

## Replacing stubs when teammates deliver

**Person 2 (BBB classifier):**
Replace `person2_functions.py` entirely. The function signature must be:
```python
def predict_bbb(smiles: str) -> dict:
    # returns {"label": bool, "probability": float}
```

**Person 3 (circadian + sleep modifiers):**
Replace `person3_functions.py` entirely. The function signatures must be:
```python
def circadian_modifier(t: float) -> float:  # multiplier on CL, t in hours
def sleep_modifier(t: float) -> float       # multiplier on CL, t in hours
```
Both must return a positive scalar. The engine floors CL at 0.001 L/hr to prevent ODE instability.

---

## Data sources

- **SMILES**: PubChem REST API (`/rest/pug/compound/name/{drug}/property/...`)
- **PK parameters**: PK-DB (`pk-db.com/api/v1/`)
- **CYP450 inhibition**: PubChem bioassays, Veith et al. 2009 (AIDs 882, 883, 899, 1851, 1852)
- **BBB dataset**: [B3DB](https://github.com/theochem/B3DB) — 7,807 compounds with BBB+/BBB- labels
