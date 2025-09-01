from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from .dataset import year_range

METRICS_MAP = {
    "global_sales": "Global_Sales",
    "na_sales": "NA_Sales",
    "eu_sales": "EU_Sales",
    "jp_sales": "JP_Sales",
    "critic_score": "Critic_Score",
    "user_score": "User_Score",
}


def overview(df: pd.DataFrame) -> dict:
    """Estatísticas descritivas de alto nível do dataset."""
    yr = year_range(df)
    return {
        "total_titles": int(df["Name"].nunique()),
        "year_range": yr,
        "sum_global_sales": None if df["Global_Sales"].dropna().empty else round(float(df["Global_Sales"].sum()), 2),
        "avg_critic_score": None if df["Critic_Score"].dropna().empty else round(float(df["Critic_Score"].mean()), 2),
        "avg_user_score": None if df["User_Score"].dropna().empty else round(float(df["User_Score"].mean()), 2),
    }


def _apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Aplica filtros comuns: ano (exato / intervalo), plataforma, gênero, publisher, rating.
    Robusto a valores inválidos e NaN.
    """
    out = df.copy()

    if filters.get("year") is not None:
        try:
            ycol = pd.to_numeric(out["Year_of_Release"], errors="coerce")
            y = float(filters["year"])
            out = out[ycol.round(0) == y]
        except Exception:
            return out.iloc[0:0] 

    if filters.get("year_from") is not None:
        try:
            ycol = pd.to_numeric(out["Year_of_Release"], errors="coerce")
            out = out[ycol >= float(filters["year_from"])]
        except Exception:
            return out.iloc[0:0]

    if filters.get("year_to") is not None:
        try:
            ycol = pd.to_numeric(out["Year_of_Release"], errors="coerce")
            out = out[ycol <= float(filters["year_to"])]
        except Exception:
            return out.iloc[0:0]

    if filters.get("platform"):
        out = out[out["Platform"].astype(str).str.lower() == str(filters["platform"]).lower()]
    if filters.get("genre"):
        out = out[out["Genre"].astype(str).str.lower() == str(filters["genre"]).lower()]
    if filters.get("publisher"):
        out = out[out["Publisher"].astype(str).str.lower() == str(filters["publisher"]).lower()]
    if filters.get("rating"):
        out = out[out["Rating"].astype(str).str.lower() == str(filters["rating"]).lower()]

    return out


def rankings(
    df: pd.DataFrame,
    metric: str,
    filters: Dict[str, Any],
    limit: int = 10,
    offset: int = 0,
) -> Tuple[int, List[dict]]:
    """
    Lista ordenada por uma métrica (desc), com filtros e paginação.
    Retorna (total, items). Faz sanitize de NaN -> None para validação Pydantic.
    """
    col = METRICS_MAP[metric]
    dff = _apply_filters(df, filters)

    dff = dff.dropna(subset=[col])
    if dff.empty:
        return 0, []

    dff = dff.sort_values(by=col, ascending=False)
    total = len(dff)
    page = dff.iloc[offset: offset + limit]

    def _s(v):  
        return None if pd.isna(v) else str(v)

    def _f(v): 
        return float(v) if pd.notna(v) else None

    def _i(v): 
        return int(v) if pd.notna(v) else None

    items: List[dict] = []
    for _, row in page.iterrows():
        items.append(
            {
                "name": str(row["Name"]),
                "platform": _s(row.get("Platform")),
                "genre": _s(row.get("Genre")),
                "year": _i(row.get("Year_of_Release")),
                "publisher": _s(row.get("Publisher")),
                "developer": _s(row.get("Developer")),
                "rating": _s(row.get("Rating")),
                "global_sales": _f(row.get("Global_Sales")),
                "na_sales": _f(row.get("NA_Sales")),
                "eu_sales": _f(row.get("EU_Sales")),
                "jp_sales": _f(row.get("JP_Sales")),
                "other_sales": _f(row.get("Other_Sales")),
                "critic_score": _f(row.get("Critic_Score")),
                "user_score": _f(row.get("User_Score")),
            }
        )

    return total, items


def best_match(df: pd.DataFrame, name: str) -> Optional[pd.Series]:
    """
    Busca um jogo por nome (case-insensitive), usando exato e depois "contains" com fallback.
    Em empate, prioriza maior vendas globais.
    """
    name_l = (name or "").lower().strip()
    if not name_l:
        return None

    exact = df[df["name_lower"] == name_l]
    if not exact.empty:
        return exact.iloc[0]

    contains = df[df["name_lower"].str.contains(name_l, na=False)]
    if not contains.empty:
        contains = contains.sort_values("Global_Sales", ascending=False)
        return contains.iloc[0]

    return None


def aggregate_metric(
    df: pd.DataFrame,
    metric: str, 
    filters: Dict[str, Any],
    name_contains: Optional[str] = None,
) -> dict:
    """
    Agrega por métrica (mean/sum) sobre um subconjunto definido por:
    - filtros usuais (ano, plataforma, gênero, ...)
    - e/ou "franquia"/termo no nome (name_contains, case-insensitive)
    """
    col = METRICS_MAP[metric]
    dff = df.copy()

    if name_contains:
        needle = str(name_contains).lower().strip()
        if needle:
            dff = dff[dff["Name"].astype(str).str.lower().str.contains(needle, na=False)]

    dff = _apply_filters(dff, filters)

    dff = dff.dropna(subset=[col])
    if dff.empty:
        return {
            "metric": metric,
            "filters": {k: v for k, v in filters.items() if v is not None},
            "name_contains": name_contains,
            "count": 0,
            "mean": None,
            "sum": None,
        }

    vals = pd.to_numeric(dff[col], errors="coerce").dropna()
    return {
        "metric": metric,
        "filters": {k: v for k, v in filters.items() if v is not None},
        "name_contains": name_contains,
        "count": int(len(vals)),
        "mean": round(float(vals.mean()), 3),
        "sum": round(float(vals.sum()), 3),
    }
