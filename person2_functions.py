"""
STUB — Person 2's BBB classifier.

Replace this file entirely when Person 2 delivers their model.
The pipeline (pipeline.py) calls: predict_bbb(smiles: str) -> dict

Expected return shape:
    {
        "label": True,        # bool — BBB penetrant or not
        "probability": 0.87,  # float in [0, 1]
    }
"""


def predict_bbb(smiles: str) -> dict:
    """
    Stub: returns a random-ish prediction based on molecule length.
    Replace with the real model.
    """
    import hashlib
    h = int(hashlib.md5(smiles.encode()).hexdigest(), 16)
    prob = round(0.3 + 0.4 * (h % 100) / 100, 3)
    return {"label": prob > 0.5, "probability": prob}
