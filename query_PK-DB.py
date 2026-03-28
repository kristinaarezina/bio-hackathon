"""
Query PK-DB for clearance, half-life, and volume of distribution for 3 demo drugs.
Saves to data/pkdb_results.json.

PK-DB API docs: https://pkdb.pk-sim.info/api/
"""

import json
import requests
from pathlib import Path

PKDB_BASE = "https://pkdb.pk-sim.info/api"
DRUGS = ["lamotrigine", "simvastatin", "midazolam"]
OUT_FILE = Path(__file__).parent / "data" / "pkdb_results.json"

# PK parameter keywords to extract
PK_KEYWORDS = ["clearance", "half-life", "vd", "volume"]


def search_substance(drug_name: str) -> list[dict]:
    """Search PK-DB for a substance by name, return list of matches."""
    r = requests.get(f"{PKDB_BASE}/substances/", params={"name": drug_name}, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])


def get_pk_outputs(substance_pk: int) -> list[dict]:
    """Fetch PK outputs for a substance by its primary key."""
    r = requests.get(
        f"{PKDB_BASE}/outputs/",
        params={"substance": substance_pk, "format": "json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def extract_pk_params(outputs: list[dict]) -> dict:
    """Pull out CL, t½, Vd values from raw output list."""
    params: dict[str, list] = {"clearance": [], "half_life": [], "vd": []}
    for o in outputs:
        ptype = (o.get("pktype") or o.get("measurement_type") or "").lower()
        value = o.get("value") or o.get("mean")
        unit = o.get("unit", "")
        if not value:
            continue
        if "clearance" in ptype or "cl" == ptype:
            params["clearance"].append({"value": value, "unit": unit})
        elif "half" in ptype or "t1/2" in ptype or "t½" in ptype:
            params["half_life"].append({"value": value, "unit": unit})
        elif "vd" in ptype or "volume" in ptype:
            params["vd"].append({"value": value, "unit": unit})
    return params


def query_drug(drug_name: str) -> dict:
    substances = search_substance(drug_name)
    if not substances:
        print(f"  {drug_name}: no results in PK-DB")
        return {"drug": drug_name, "found": False}

    subst = substances[0]
    pk_id = subst.get("pk") or subst.get("id")
    print(f"  {drug_name}: found substance pk={pk_id}, fetching outputs...")

    outputs = get_pk_outputs(pk_id)
    pk_params = extract_pk_params(outputs)

    result = {
        "drug": drug_name,
        "found": True,
        "substance": {"pk": pk_id, "name": subst.get("name")},
        "pk_params": pk_params,
        "raw_output_count": len(outputs),
    }
    print(f"    CL entries:  {len(pk_params['clearance'])}")
    print(f"    t½ entries:  {len(pk_params['half_life'])}")
    print(f"    Vd entries:  {len(pk_params['vd'])}")
    return result


def query_all_drugs() -> dict:
    OUT_FILE.parent.mkdir(exist_ok=True)
    results = {}
    for drug in DRUGS:
        print(f"\nQuerying PK-DB for {drug}...")
        try:
            results[drug] = query_drug(drug)
        except requests.HTTPError as e:
            print(f"  HTTP error: {e}")
            results[drug] = {"drug": drug, "found": False, "error": str(e)}
        except Exception as e:
            print(f"  Error: {e}")
            results[drug] = {"drug": drug, "found": False, "error": str(e)}

    OUT_FILE.write_text(json.dumps(results, indent=2))
    print(f"\nSaved to {OUT_FILE}")
    return results


if __name__ == "__main__":
    query_all_drugs()
