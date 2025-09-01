import os
import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

def get_api_url():
    if "API_URL" not in st.session_state:
        st.session_state.API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
    return st.session_state.API_URL

st.set_page_config(page_title="IA Games", layout="wide")
st.sidebar.header("Configuração")
st.sidebar.text_input("API URL", key="API_URL", value=get_api_url())
API_URL = st.session_state.API_URL

st.title("🎮 IA Games — Dashboard e Busca")

def fetch_json(path, params=None, method="GET", payload=None, api_url=None, timeout=12):
    base = api_url or API_URL
    url = f"{base}{path}"
    try:
        if method.upper() == "GET":
            r = requests.get(url, params=params, timeout=timeout)
        else:
            r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Falha ao chamar {url}: {e}")
        return None

@st.cache_data(ttl=300, show_spinner=False)
def load_overview(api_url: str):
    return fetch_json("/stats/overview", api_url=api_url)

@st.cache_data(ttl=300, show_spinner=False)
def bootstrap_meta(api_url: str):
    """
    Tenta ler plataformas/genres de endpoints 'meta' (se existirem).
    Caso não existam, coleta a partir de /rankings/games paginando por offset.
    Também retorna anos possíveis a partir do overview.
    """
    platforms: set[str] = set()
    genres: set[str] = set()

    ov = load_overview(api_url) or {}
    yr = ov.get("year_range") or [2000, 2015]
    years = []
    try:
        y0 = int(yr[0]) if yr and yr[0] is not None else 2000
        y1 = int(yr[1]) if yr and yr[1] is not None else 2015
        if y0 > y1:
            y0, y1 = y1, y0
        years = list(range(y0, y1 + 1))
    except Exception:
        years = list(range(2000, 2016))

    meta_plat = fetch_json("/meta/platforms", api_url=api_url)
    if meta_plat and isinstance(meta_plat, dict):
        arr = meta_plat.get("items") or meta_plat.get("platforms") or []
        for p in arr:
            if p: platforms.add(str(p))

    meta_gen = fetch_json("/meta/genres", api_url=api_url)
    if meta_gen and isinstance(meta_gen, dict):
        arr = meta_gen.get("items") or meta_gen.get("genres") or []
        for g in arr:
            if g: genres.add(str(g))

    if not platforms or not genres:
        LIMIT = 100
        for offset in range(0, 1000, LIMIT):
            params = {"metric": "global_sales", "limit": LIMIT, "offset": offset}
            data = fetch_json("/rankings/games", params=params, api_url=api_url)
            items = (data or {}).get("items") or []
            if not items:
                break
            for it in items:
                p = it.get("platform")
                g = it.get("genre")
                if p: platforms.add(str(p))
                if g: genres.add(str(g))

    plats = sorted(platforms) if platforms else []
    gens = sorted(genres) if genres else []

    return {
        "years": years,
        "platforms": plats,
        "genres": gens,
    }

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Panorama", "Rankings", "Explorar", "Franquias/Agregados", "Perguntas (NLQ)"])

with tab1:
    st.subheader("Visão geral do dataset")
    ov = load_overview(API_URL)
    if ov:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Títulos únicos", ov.get("total_titles"))
        yr = ov.get("year_range") or [None, None]
        c2.metric("Período (min)", yr[0])
        c3.metric("Período (max)", yr[1])
        c4.metric("Vendas globais (mi)", ov.get("sum_global_sales"))
        c5.metric("Nota média crítica", ov.get("avg_critic_score"))

        st.divider()

        st.markdown("### 🏆 Top 10 por **vendas globais**")
        res_top = fetch_json("/rankings/games", params={"metric": "global_sales", "limit": 10})
        items_top = (res_top or {}).get("items") or []
        if items_top:
            df_top = pd.DataFrame(items_top)
            cols_keep = [c for c in ["name", "platform", "genre", "global_sales", "year"] if c in df_top.columns]
            st.dataframe(df_top[cols_keep], width="stretch")
            fig = plt.figure()
            names = df_top["name"][:10][::-1]
            vals = df_top["global_sales"][:10][::-1]
            plt.barh(names, vals)
            plt.xlabel("Vendas globais (milhões)")
            plt.ylabel("Jogo")
            st.pyplot(fig)
        else:
            st.info("Sem dados para o Top 10.")

        st.divider()

        st.markdown("### 📈 Evolução do Top 1 por ano (vendas globais)")
        col_a, col_b = st.columns(2)
        default_start = int(yr[0]) if yr and yr[0] else 2000
        default_end = int(yr[1]) if yr and yr[1] else 2015
        year_from = col_a.number_input("Ano inicial", value=default_start, step=1)
        year_to = col_b.number_input("Ano final", value=default_end, step=1)
        if year_from <= year_to:
            years = list(range(int(year_from), int(year_to) + 1))
            vals = []
            for y in years:
                r = fetch_json("/rankings/games", params={"metric": "global_sales", "year": y, "limit": 1})
                items_y = (r or {}).get("items") or []
                v = items_y[0].get("global_sales", 0) if items_y else 0
                vals.append(v or 0)
            fig2 = plt.figure()
            plt.plot(years, vals, marker="o")
            plt.xlabel("Ano")
            plt.ylabel("Vendas do Top 1 (mi)")
            st.pyplot(fig2)

with tab2:
    st.subheader("Rankings de jogos")

    meta = bootstrap_meta(API_URL)
    years = meta.get("years") or []
    platforms = meta.get("platforms") or []
    genres = meta.get("genres") or []

    c = st.columns(5)
    metric = c[0].selectbox("Métrica", ["global_sales", "na_sales", "eu_sales", "jp_sales", "critic_score", "user_score"])

    year_opts = ["Sem filtro"] + years
    sel_year = c[1].selectbox("Ano", options=year_opts, index=0)
    plat_opts = ["Sem filtro"] + platforms if platforms else ["Sem filtro"]
    sel_plat = c[2].selectbox("Plataforma", options=plat_opts, index=0)

    gen_opts = ["Sem filtro"] + genres if genres else ["Sem filtro"]
    sel_genre = c[3].selectbox("Gênero", options=gen_opts, index=0)

    limit = c[4].slider("Limite", 5, 50, 10)

    params = {"metric": metric, "limit": int(limit)}
    # Ano
    if isinstance(sel_year, int):
        params["year"] = sel_year
    elif isinstance(sel_year, str) and sel_year != "Sem filtro":
        try:
            params["year"] = int(sel_year)
        except Exception:
            pass
    # Plataforma e gen
    if sel_plat and sel_plat != "Sem filtro":
        params["platform"] = sel_plat
    if sel_genre and sel_genre != "Sem filtro":
        params["genre"] = sel_genre

    data = fetch_json("/rankings/games", params=params)
    items = (data or {}).get("items") or []
    if items:
        df = pd.DataFrame(items)
        st.dataframe(df, width="stretch")
        if metric in df.columns and not df.empty:
            fig = plt.figure()
            plt.barh(df["name"][:10][::-1], df[metric][:10][::-1])
            plt.xlabel(metric)
            plt.ylabel("Jogo")
            st.pyplot(fig)
    else:
        st.info("Nenhum resultado para os filtros atuais.")

with tab3:
    st.subheader("Explorar com autocomplete")
    query = st.text_input("Digite parte do nome do jogo", placeholder="ex.: zelda, mario, fifa...")

    suggestions = []
    if query.strip():
        resp = fetch_json("/games/suggest", params={"q": query.strip(), "limit": 10})
        suggestions = (resp or {}).get("items") or []

    selected = None
    if suggestions:
        selected = st.selectbox("Sugestões", suggestions, index=0)
        st.caption("Sugestões rápidas:")
        cols = st.columns(min(5, len(suggestions)))
        for i, name in enumerate(suggestions[:5]):
            if cols[i].button(name, key=f"sugg_{i}"):
                selected = name

    name_to_fetch = selected or (query.strip() if query else None)
    if name_to_fetch:
        detail = fetch_json(f"/games/{name_to_fetch}")
        if detail:
            st.markdown("### 🧾 Detalhes do jogo")
            d = detail
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Plataforma", d.get("platform") or "—")
            m2.metric("Gênero", d.get("genre") or "—")
            m3.metric("Ano", d.get("year") or "—")
            m4.metric("Rating", d.get("rating") or "—")

            m5, m6, m7 = st.columns(3)
            m5.metric("Vendas globais (mi)", d.get("global_sales") or 0)
            m6.metric("Crítica (avg)", d.get("critic_score") or "—")
            m7.metric("Usuários (avg)", d.get("user_score") or "—")

            regions = {
                "NA": d.get("na_sales"),
                "EU": d.get("eu_sales"),
                "JP": d.get("jp_sales"),
                "Other": d.get("other_sales"),
            }
            reg_items = [(k, v) for k, v in regions.items() if v is not None]
            if reg_items:
                st.markdown("#### Vendas por região (mi)")
                fig = plt.figure()
                labels = [k for k, _ in reg_items]
                values = [v for _, v in reg_items]
                plt.bar(labels, values)
                plt.xlabel("Região")
                plt.ylabel("Vendas (mi)")
                st.pyplot(fig)

            df_detail = pd.DataFrame([{
                "name": d.get("name"),
                "platform": d.get("platform"),
                "genre": d.get("genre"),
                "year": d.get("year"),
                "publisher": d.get("publisher"),
                "developer": d.get("developer"),
                "rating": d.get("rating"),
                "global_sales": d.get("global_sales"),
                "critic_score": d.get("critic_score"),
                "user_score": d.get("user_score"),
            }])
            st.dataframe(df_detail, width="stretch")
        else:
            st.warning("Jogo não encontrado.")

with tab4:
    st.subheader("Média/Soma por franquia (termo no nome) — /stats/aggregate")

    meta = meta if "meta" in locals() else bootstrap_meta(API_URL)
    years = meta.get("years") or []
    platforms = meta.get("platforms") or []
    genres = meta.get("genres") or []

    term = st.text_input("Termo/franquia no nome", placeholder="ex.: zelda, mario, pokemon...").strip()
    metric = st.selectbox("Métrica", ["critic_score", "user_score", "global_sales", "na_sales", "eu_sales", "jp_sales"])

    c = st.columns(4)
    plat_opts = ["Sem filtro"] + platforms if platforms else ["Sem filtro"]
    sel_plat = c[0].selectbox("Plataforma (opcional)", options=plat_opts, index=0)

    gen_opts = ["Sem filtro"] + genres if genres else ["Sem filtro"]
    sel_genre = c[1].selectbox("Gênero (opcional)", options=gen_opts, index=0)

    year_opts = ["Sem filtro"] + years
    sel_yfrom = c[2].selectbox("Ano inicial", options=year_opts, index=0)
    sel_yto = c[3].selectbox("Ano final", options=year_opts, index=0)

    if st.button("Calcular agregados", type="primary"):
        if not term:
            st.warning("Digite um termo/franquia (ex.: zelda, mario).")
        else:
            params = {"metric": metric, "name_contains": term}
            if sel_plat != "Sem filtro": params["platform"] = sel_plat
            if sel_genre != "Sem filtro": params["genre"] = sel_genre

            y_from_val = None
            y_to_val = None
            try:
                y_from_val = int(sel_yfrom) if isinstance(sel_yfrom, int) else (int(sel_yfrom) if sel_yfrom != "Sem filtro" else None)
            except Exception:
                y_from_val = None
            try:
                y_to_val = int(sel_yto) if isinstance(sel_yto, int) else (int(sel_yto) if sel_yto != "Sem filtro" else None)
            except Exception:
                y_to_val = None

            if y_from_val is not None: params["year_from"] = y_from_val
            if y_to_val is not None: params["year_to"] = y_to_val

            agg = fetch_json("/stats/aggregate", params=params)
            if agg:
                c1, c2, c3 = st.columns(3)
                c1.metric("Qtd. títulos", agg.get("count", 0))
                c2.metric("Média", agg.get("mean"))
                c3.metric("Soma", agg.get("sum"))

                st.divider()
                st.markdown("### Evolução anual (soma)")

                ov2 = load_overview(API_URL) or {}
                yr2 = ov2.get("year_range") or [2000, 2015]
                y_start = y_from_val if y_from_val is not None else int(yr2[0] or 2000)
                y_end = y_to_val if y_to_val is not None else int(yr2[1] or y_start)

                if y_start > y_end:
                    y_start, y_end = y_end, y_start

                years_plot, sums_plot = [], []
                for y in range(y_start, y_end + 1):
                    p = dict(params)
                    p.pop("year_from", None)
                    p.pop("year_to", None)
                    p["year"] = y
                    r = fetch_json("/stats/aggregate", params=p) or {}
                    years_plot.append(y)
                    sums_plot.append(r.get("sum") or 0)

                if years_plot:
                    fig = plt.figure()
                    plt.plot(years_plot, sums_plot, marker="o")
                    plt.xlabel("Ano")
                    plt.ylabel(f"Soma anual de {metric}")
                    st.pyplot(fig)
            else:
                st.info("Sem dados para os filtros informados.")

with tab5:
    st.subheader("Pergunte em linguagem natural — /ask")

    colL, colR = st.columns([2, 1])
    with colL:
        user_q = st.text_input(
            "Digite sua pergunta",
            key="nlq_input",
            placeholder="ex.: Quais são os jogos mais vendidos em 2010?"
        )
    with colR:
        ask_click = st.button("Perguntar", type="primary")

    st.caption("Exemplos rápidos:")
    example_queries = [
        "Quais são os jogos mais vendidos em 2010?",
        "Top nota crítica no PS3 em 2009",
        "Top vendas no Japão no Nintendo DS",
        "Top EU sales em 2015",
        "Jogos com melhor user score no PC",
        "Top vendas NA de Sports em 2008",
        "Mais vendidos no Wii",
        "Qual a média de nota da franquia Zelda?",
        "Média do user score da franquia Mario no Wii",
        "Soma das vendas globais da franquia Pokemon no DS de 2006 a 2010",
    ]
    cols_ex = st.columns(3)
    example_clicked = None
    for i, qex in enumerate(example_queries):
        if cols_ex[i % 3].button(qex, key=f"btn_ex_{i}"):
            example_clicked = qex

    def render_ask_result(q: str):
        st.markdown(f"**Pergunta:** {q}")
        res = fetch_json("/ask", method="POST", payload={"question": q})
        if not res:
            st.warning("Falha ao consultar o /ask.")
            return

        mode = res.get("mode") or "rankings"
        if mode == "aggregate":
            agg = res.get("aggregate") or {}
            c1, c2, c3 = st.columns(3)
            c1.metric("Qtd. títulos", agg.get("count", 0))
            c2.metric("Média", agg.get("mean"))
            c3.metric("Soma", agg.get("sum"))

            parsed = res.get("parsed") or {}
            name_contains = parsed.get("name_contains")
            metric = parsed.get("metric", "critic_score")
            filters = parsed.get("filters") or {}

            ov = load_overview(API_URL) or {}
            yr = ov.get("year_range") or [2000, 2015]
            y0 = int(yr[0] or 2000); y1 = int(yr[1] or y0)
            years, sums = [], []
            for y in range(y0, y1 + 1):
                p = {"metric": metric, "name_contains": name_contains, **filters, "year": y}
                r = fetch_json("/stats/aggregate", params=p) or {}
                years.append(y); sums.append(r.get("sum") or 0)

            st.markdown("##### Evolução anual (soma)")
            fig = plt.figure()
            plt.plot(years, sums, marker="o")
            plt.xlabel("Ano")
            plt.ylabel(f"Soma anual de {metric}")
            st.pyplot(fig)
        else:
            items = res.get("items") or []
            if items:
                df = pd.DataFrame(items)
                st.dataframe(df, width="stretch")
                parsed = res.get("parsed") or {}
                metric = (parsed.get("metric") or "global_sales")
                if metric in df.columns and not df.empty:
                    st.markdown("##### Top N (gráfico)")
                    fig = plt.figure()
                    plt.barh(df["name"][:10][::-1], df[metric][:10][::-1])
                    plt.xlabel(metric)
                    plt.ylabel("Jogo")
                    st.pyplot(fig)
            else:
                st.info("Sem resultados para a pergunta.")

    if ask_click and user_q.strip():
        render_ask_result(user_q.strip())

    if example_clicked:
        render_ask_result(example_clicked)
