"""
Pull canonical SMILES for 3 demo drugs from PubChem.
Saves to data/drug_smiles.json.
"""

import json
import requests
from pathlib import Path

DRUGS = ["lamotrigine", "simvastatin", "midazolam"]
OUT_FILE = Path(__file__).parent / "data" / "drug_smiles.json"


def get_smiles(drug_name: str) -> dict:
    url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}"
        "/property/CanonicalSMILES,IsomericSMILES,ConnectivitySMILES,MolecularWeight/JSON"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    props = r.json()["PropertyTable"]["Properties"][0]
    # PubChem returns whichever SMILES variant it has; prefer canonical, fall back
    smiles = (
        props.get("CanonicalSMILES")
        or props.get("IsomericSMILES")
        or props.get("ConnectivitySMILES")
    )
    return {
        "smiles": smiles,
        "mol_weight": props.get("MolecularWeight"),
        "cid": props.get("CID"),
    }


def pull_all_smiles() -> dict:
    OUT_FILE.parent.mkdir(exist_ok=True)
    results = {}
    for drug in DRUGS:
        print(f"Fetching {drug}...")
        results[drug] = get_smiles(drug)
        print(f"  CID={results[drug]['cid']}  MW={results[drug]['mol_weight']}")
        print(f"  SMILES: {results[drug]['smiles']}")
    OUT_FILE.write_text(json.dumps(results, indent=2))
    print(f"\nSaved to {OUT_FILE}")
    return results


if __name__ == "__main__":
    pull_all_smiles()
