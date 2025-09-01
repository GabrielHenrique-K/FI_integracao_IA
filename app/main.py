from typing import Optional, Dict, Any
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .deps import get_df
from .schemas import Overview, RankingResponse, GameItem
from .observability.metrics import setup_metrics
from .services.queries import (
    overview as overview_fn,
    rankings,
    best_match,
    METRICS_MAP,
    aggregate_metric,
)
from .services.suggest import suggest_names
from .services.nlq import parse_question


app = FastAPI(title="IA Games API", version="1.2.0")

setup_metrics(app)


@app.on_event("startup")
def startup_event():

    _ = get_df()

@app.get("/healthz")
def healthz():
    try:
        df = get_df()
        return {"status": "ok", "dataset_loaded": True, "rows": len(df)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/meta/platforms")
def meta_platforms():
    df = get_df()
    plats = sorted(str(p) for p in df["Platform"].dropna().unique())
    return {"items": plats, "count": len(plats)}

@app.get("/meta/genres")
def meta_genres():
    df = get_df()
    gens = sorted(str(g) for g in df["Genre"].dropna().unique())
    return {"items": gens, "count": len(gens)}

@app.get("/meta/years")
def meta_years():
    import pandas as pd
    df = get_df()
    years = (
        pd.to_numeric(df["Year_of_Release"], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )
    years = sorted(set(years))
    return {"items": years, "count": len(years)}

@app.get("/stats/overview", response_model=Overview)
def stats_overview():
    df = get_df()
    return overview_fn(df)


@app.get("/stats/aggregate")
def stats_aggregate(
    metric: str = Query("critic_score", enum=list(METRICS_MAP.keys())),
    name_contains: Optional[str] = None,
    year: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    platform: Optional[str] = None,
    genre: Optional[str] = None,
    publisher: Optional[str] = None,
    rating: Optional[str] = None,
):
    """
    Agregações por "franquia"/termo no nome + filtros: média e soma da métrica.
    Exemplos:
      - /stats/aggregate?metric=critic_score&name_contains=zelda
      - /stats/aggregate?metric=user_score&name_contains=mario&platform=Wii
    """
    df = get_df()
    filters = {
        "year": year,
        "year_from": year_from,
        "year_to": year_to,
        "platform": platform,
        "genre": genre,
        "publisher": publisher,
        "rating": rating,
    }
    return aggregate_metric(df, metric=metric, filters=filters, name_contains=name_contains)

@app.get("/rankings/games", response_model=RankingResponse)
def rankings_games(
    metric: str = Query("global_sales", enum=list(METRICS_MAP.keys())),
    year: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    platform: Optional[str] = None,
    genre: Optional[str] = None,
    publisher: Optional[str] = None,
    rating: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    df = get_df()
    filters = {
        "year": year,
        "year_from": year_from,
        "year_to": year_to,
        "platform": platform,
        "genre": genre,
        "publisher": publisher,
        "rating": rating,
    }
    total, items = rankings(df, metric=metric, filters=filters, limit=limit, offset=offset)
    return {
        "metric": metric,
        "filters": {k: v for k, v in filters.items() if v is not None},
        "total": total,
        "items": items,
    }


@app.get("/games/suggest")
def games_suggest(q: str, limit: int = 10):
    df = get_df()
    return {"q": q, "items": suggest_names(df, q, limit=limit)}


@app.get("/games/{name}", response_model=GameItem)
def game_details(name: str):
    df = get_df()
    row = best_match(df, name)
    if row is None:
        suggestions = suggest_names(df, name, limit=1)
        if not suggestions:
            raise HTTPException(status_code=404, detail="Game not found")
        row = best_match(df, suggestions[0])
        if row is None:
            raise HTTPException(status_code=404, detail="Game not found")

    def _s(v): return None if pd.isna(v) else str(v)
    def _f(v): return float(v) if pd.notna(v) else None
    def _i(v): return int(v) if pd.notna(v) else None

    item = {
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
    return item


@app.post("/ask")
def ask(payload: Dict[str, Any]):
    """
    NLQ simples:
      - "Quais são os jogos mais vendidos em 2010?"
         -> mode=rankings, metric=global_sales, filters={year:2010}
      - "Qual a média de nota da franquia Zelda?"
         -> mode=aggregate, metric=critic_score (ou user_score), name_contains="zelda"
    """
    question = (payload.get("question") or "").strip()
    parsed = parse_question(question)
    df = get_df()

    if parsed.get("mode") == "aggregate":
        agg = aggregate_metric(
            df,
            metric=parsed["metric"],
            filters=parsed.get("filters") or {},
            name_contains=parsed.get("name_contains"),
        )
        return {
            "question": question,
            "mode": "aggregate",
            "parsed": parsed,
            "aggregate": agg,
            "items": [],
        }

    total, items = rankings(
        df,
        metric=parsed["metric"],
        filters=parsed.get("filters") or {},
        limit=int(parsed.get("limit") or 10),
        offset=0,
    )
    return {
        "question": question,
        "mode": "rankings",
        "parsed": parsed,
        "total": total,
        "items": items,
    }
