"""
CYP450 dataset loader — pulls from PubChem bioassays (Veith et al. 2009).
Five isoforms: CYP1A2, CYP2C9, CYP2C19, CYP2D6, CYP3A4.
Saves to data/cyp450_clean.parquet.
"""

import time
import requests
import pandas as pd
from pathlib import Path
from io import StringIO

# Veith et al. 2009 PubChem AID numbers for each CYP isoform
CYP_AIDS = {
    "CYP1A2":  882,
    "CYP2C9":  883,
    "CYP2C19": 899,
    "CYP2D6":  1852,
    "CYP3A4":  1851,
}

DATA_DIR = Path(__file__).parent / "data"
OUT_FILE = DATA_DIR / "cyp450_clean.parquet"
CACHE_DIR = DATA_DIR / "cyp450_cache"


def download_assay(aid: int, cyp_name: str) -> pd.DataFrame:
    """Download concise CSV for one PubChem assay and return active/inactive labels."""
    cache_file = CACHE_DIR / f"aid{aid}.csv"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        print(f"  {cyp_name}: using cached file")
        df = pd.read_csv(cache_file)
    else:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/assay/aid/{aid}/concise/CSV"
        print(f"  {cyp_name}: downloading AID {aid}...")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text), skiprows=1)  # row 0 is a comment
        df.to_csv(cache_file, index=False)
        time.sleep(0.3)  # be polite to NCBI

    # PubChem concise CSV columns: PUBCHEM_AID, PUBCHEM_SID, PUBCHEM_CID,
    # PUBCHEM_ACTIVITY_OUTCOME (Active/Inactive/Inconclusive)
    df = df[["PUBCHEM_CID", "PUBCHEM_ACTIVITY_OUTCOME"]].dropna(subset=["PUBCHEM_CID"])
    df["PUBCHEM_CID"] = df["PUBCHEM_CID"].astype(int)
    df[cyp_name] = (df["PUBCHEM_ACTIVITY_OUTCOME"].str.lower() == "active").astype(int)
    return df[["PUBCHEM_CID", cyp_name]]


def fetch_smiles_batch(cids: list[int], batch_size: int = 100) -> dict[int, str]:
    """Fetch canonical SMILES for a list of PubChem CIDs."""
    smiles_map: dict[int, str] = {}
    total = len(cids)
    for i in range(0, total, batch_size):
        batch = cids[i : i + batch_size]
        cid_str = ",".join(map(str, batch))
        url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid_str}"
            "/property/CanonicalSMILES/JSON"
        )
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            for prop in r.json()["PropertyTable"]["Properties"]:
                smiles_map[prop["CID"]] = prop["CanonicalSMILES"]
        except Exception as e:
            print(f"  SMILES batch {i//batch_size} failed: {e}")
        time.sleep(0.3)
        if i % 500 == 0 and i > 0:
            print(f"  fetched SMILES for {i}/{total} compounds...")
    return smiles_map


def build_cyp450_dataset(add_smiles: bool = True) -> pd.DataFrame:
    """
    Download all 5 CYP assays, merge on CID, optionally add SMILES.
    Returns DataFrame with columns: CID, SMILES (optional), CYP1A2, CYP2C9, CYP2C19, CYP2D6, CYP3A4.
    """
    DATA_DIR.mkdir(exist_ok=True)

    print("Downloading CYP450 assays from PubChem...")
    merged = None
    for cyp_name, aid in CYP_AIDS.items():
        df = download_assay(aid, cyp_name)
        merged = df if merged is None else merged.merge(df, on="PUBCHEM_CID", how="outer")

    merged = merged.rename(columns={"PUBCHEM_CID": "CID"})
    # Fill NaN (compound not tested in that assay) as -1 (unknown)
    for col in CYP_AIDS:
        merged[col] = merged[col].fillna(-1).astype(int)

    if add_smiles:
        print(f"Fetching SMILES for {len(merged)} compounds (this takes a few minutes)...")
        cids = merged["CID"].tolist()
        smiles_map = fetch_smiles_batch(cids)
        merged["smiles"] = merged["CID"].map(smiles_map)
        # Reorder columns
        cols = ["CID", "smiles"] + list(CYP_AIDS.keys())
        merged = merged[cols].dropna(subset=["smiles"])

    merged.to_parquet(OUT_FILE, index=False)
    print(f"Saved {len(merged)} compounds to {OUT_FILE}")
    return merged


def load_cyp450() -> pd.DataFrame:
    """Load from cache if available, else download."""
    if OUT_FILE.exists():
        print(f"Loading cached CYP450 dataset from {OUT_FILE}")
        return pd.read_parquet(OUT_FILE)
    return build_cyp450_dataset()


if __name__ == "__main__":
    # Quick mode: download labels only (no SMILES fetch), fast for hackathon
    import sys
    fast = "--fast" in sys.argv
    df = build_cyp450_dataset(add_smiles=not fast)
    print(df.head())
    print(f"\nShape: {df.shape}")
    print(f"Active rates:\n{df[list(CYP_AIDS.keys())].apply(lambda c: (c==1).sum())}")
