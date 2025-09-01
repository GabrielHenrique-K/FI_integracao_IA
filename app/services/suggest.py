from typing import List
import pandas as pd
from rapidfuzz import process, fuzz
def suggest_names(df: pd.DataFrame, q: str, limit: int = 10) -> List[str]:
    q = (q or "").strip().lower()
    if not q:
        return []
    pref = df.loc[df["name_lower"].str.startswith(q, na=False), "Name"].head(limit).tolist()
    if len(pref) >= limit:
        return pref[:limit]
    candidates = df["Name"].astype(str).unique().tolist()
    fuzzed = process.extract(q, candidates, scorer=fuzz.WRatio, limit=limit*2)
    names = [name for name, score, _ in fuzzed if name not in pref]
    return (pref + names)[:limit]
