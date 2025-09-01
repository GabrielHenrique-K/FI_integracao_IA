from fastapi.testclient import TestClient
from app.main import app
from pathlib import Path
from datetime import datetime
import json
import random

client = TestClient(app)

def jdump(obj, max_len=1200):
    try:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        s = str(obj)
    if len(s) > max_len:
        return s[:max_len] + "... [truncated]"
    return s

def log_title(title: str):
    print("\n" + "=" * 30)
    print(title)
    print("=" * 30)

def log_req(method: str, path: str, params=None, payload=None):
    print(f"\n→ {method} {path}")
    if params:
        print("  params:", jdump(params, 600))
    if payload:
        print("  payload:", jdump(payload, 600))

def log_resp(resp):
    print("  status:", resp.status_code)
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    print("  response:", jdump(data, 1200))
    return data

def test_api_full_e2e_and_print_everything():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    log_title("1) Overview")
    log_req("GET", "/stats/overview")
    r = client.get("/stats/overview")
    data_over = log_resp(r)
    assert r.status_code == 200
    year_range = data_over.get("year_range") or [2000, 2015]
    y0 = int(year_range[0] or 2000)
    y1 = int(year_range[1] or y0)

    log_title("2) Meta")
    log_req("GET", "/meta/platforms")
    r = client.get("/meta/platforms")
    meta_plat = log_resp(r)
    assert r.status_code == 200
    platforms = meta_plat.get("items") or []

    log_req("GET", "/meta/genres")
    r = client.get("/meta/genres")
    meta_gen = log_resp(r)
    assert r.status_code == 200
    genres = meta_gen.get("items") or []

    log_req("GET", "/meta/years")
    r = client.get("/meta/years")
    meta_years = log_resp(r)
    assert r.status_code == 200
    years = meta_years.get("items") or list(range(y0, y1 + 1))

    some_year = years[len(years)//2] if years else y0
    some_plat = platforms[0] if platforms else None
    some_gen  = genres[0] if genres else None

    log_title("3) Rankings - métricas e filtros")
    metrics = ["global_sales", "critic_score", "user_score", "na_sales", "eu_sales", "jp_sales"]
    for m in metrics:
        params = {"metric": m, "limit": 5}
        if some_year:
            params["year"] = int(some_year)
        if some_plat:
            params["platform"] = some_plat
        if some_gen:
            params["genre"] = some_gen
        log_req("GET", "/rankings/games", params=params)
        r = client.get("/rankings/games", params=params)
        data_rank = log_resp(r)
        assert r.status_code == 200
        assert "items" in data_rank
        items = data_rank.get("items") or []
        print("  Top3:", "; ".join([f"{it.get('name')}({it.get(m)})" for it in items[:3]]))

    log_title("4) Game details + suggest")
    log_req("GET", "/rankings/games", params={"metric": "global_sales", "limit": 3})
    r = client.get("/rankings/games", params={"metric": "global_sales", "limit": 3})
    data_rank_simple = log_resp(r)
    assert r.status_code == 200
    items_simple = data_rank_simple.get("items") or []
    target_name = items_simple[0]["name"] if items_simple else None

    if target_name:
        path = f"/games/{target_name}"
        log_req("GET", path)
        r = client.get(path)
        data_game = log_resp(r)
        assert r.status_code == 200
        assert data_game.get("name")

    for q in ["zelda", "mario", "pokemon", "the"]:
        log_req("GET", "/games/suggest", params={"q": q, "limit": 5})
        r = client.get("/games/suggest", params={"q": q, "limit": 5})
        data_sugg = log_resp(r)
        assert r.status_code == 200

    log_title("5) Aggregate por franquia/termo")
    terms_try = ["zelda", "mario", "pokemon"]
    if target_name:
        split = [t for t in target_name.lower().split() if len(t) > 3]
        if split:
            terms_try.append(split[0])

    for term in terms_try:
        params = {"metric": "critic_score", "name_contains": term}
        log_req("GET", "/stats/aggregate", params=params)
        r = client.get("/stats/aggregate", params=params)
        data_agg = log_resp(r)
        assert r.status_code == 200
        params2 = {"metric": "global_sales", "name_contains": term, "year_from": y0, "year_to": y1}
        log_req("GET", "/stats/aggregate", params=params2)
        r2 = client.get("/stats/aggregate", params=params2)
        data_agg2 = log_resp(r2)
        assert r2.status_code == 200

    log_title("6) /ask — NLQ")
    questions = [
        "Quais são os jogos mais vendidos em 2010?",
        "Top nota crítica no PS3 em 2009",
        "Top vendas no Japão no Nintendo DS",
        "Jogos com melhor user score no PC",
        "Qual a média de nota da franquia Zelda?",
        "Soma das vendas globais da franquia Pokemon no DS de 2006 a 2010",
    ]
    for q in questions:
        payload = {"question": q}
        log_req("POST", "/ask", payload=payload)
        r = client.post("/ask", json=payload)
        data_ask = log_resp(r)
        assert r.status_code == 200
        assert data_ask.get("mode") in ("rankings", "aggregate")

    print("\n✔️  Execução concluída.")
