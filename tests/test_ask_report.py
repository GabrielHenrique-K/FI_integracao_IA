from fastapi.testclient import TestClient
from app.main import app
from pathlib import Path
from datetime import datetime
import json, csv

QUESTIONS = [
    "Quais são os jogos mais vendidos em 2010?",
    "Top nota crítica no PS3 em 2009",
    "Top vendas no Japão no Nintendo DS",
    "Top EU sales em 2015",
    "Jogos com melhor user score no PC",
    "Top vendas NA de Sports em 2008",
    "Mais vendidos no Wii",
    "Top Metacritic para Action em 2012",
]

def test_ask_batch_generates_report():
    client = TestClient(app)

    r = client.get("/healthz")
    assert r.status_code == 200, f"/healthz falhou: {r.text}"

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = reports_dir / f"ask_run_{ts}.jsonl"
    csv_path   = reports_dir / f"ask_run_{ts}.csv"
    md_path    = reports_dir / f"ask_run_{ts}.md"

    print("\n==== IA Games — Execução de testes do /ask ====\n")

    with jsonl_path.open("w", encoding="utf-8") as jf, \
         csv_path.open("w", newline="", encoding="utf-8") as cf, \
         md_path.open("w", encoding="utf-8") as mf:

        writer = csv.writer(cf)
        writer.writerow(["question", "metric", "filters", "total", "top1_name", "top1_metric_value"])

        mf.write("# IA Games — Relatório de execução do /ask\n\n")
        mf.write(f"_timestamp: {ts}_\n\n---\n")

        for idx, q in enumerate(QUESTIONS, start=1):
            print(f"[{idx}/{len(QUESTIONS)}] Pergunta: {q}")
            resp = client.post("/ask", json={"question": q})
            assert resp.status_code == 200, f"/ask falhou para '{q}' ({resp.status_code}): {resp.text}"
            data = resp.json()

            parsed = data.get("parsed") or {}
            metric = parsed.get("metric") or data.get("metric") or "global_sales"
            filters = parsed.get("filters") or {}
            items = data.get("items") or []
            total = data.get("total", len(items))

            top3 = []
            for item in items[:3]:
                top3.append(f"{item.get('name')} ({item.get(metric)})")

            print(f"→ Métrica: {metric} | Filtros: {filters} | Total: {total}")
            print("→ Top 3:", "; ".join(top3) if top3 else "—")

            jf.write(json.dumps({"question": q, "response": data}, ensure_ascii=False) + "\n")

            top1_name = items[0]["name"] if items else None
            top1_val  = items[0].get(metric) if items else None
            writer.writerow([q, metric, json.dumps(filters, ensure_ascii=False), total, top1_name, top1_val])

            mf.write(f"## {idx}. {q}\n\n")
            mf.write(f"- Métrica: `{metric}`\n- Filtros: `{filters}`\n- Total: `{total}`\n")
            if items:
                mf.write("\nTop 3:\n")
                for i, item in enumerate(items[:3], start=1):
                    mf.write(f"  {i}. {item.get('name')} — {metric}={item.get(metric)}\n")
            else:
                mf.write("\nSem resultados.\n")
            mf.write("\n---\n")

    print("\nRelatórios salvos em:")
    print(f" - {md_path}\n")
