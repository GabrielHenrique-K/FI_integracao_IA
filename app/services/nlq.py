import re
from typing import Dict, Any

PLATFORM_ALIASES = {
    "ps": "PS", "ps1": "PS", "ps2": "PS2", "ps3": "PS3", "ps4": "PS4", "ps5": "PS5",
    "x360": "X360", "xbox360": "X360", "xbox 360": "X360",
    "xbone": "XOne", "xone": "XOne", "xbox one": "XOne",
    "xbox": "XB", "xb": "XB",
    "wii": "Wii", "wiiu": "WiiU", "wii u": "WiiU",
    "ds": "DS", "3ds": "3DS", "n3ds": "3DS",
    "switch": "Switch", "nsw": "Switch",
    "n64": "N64", "gc": "GC", "gamecube": "GC",
    "gba": "GBA", "gb": "GB", "psp": "PSP", "psvita": "PSV",
    "pc": "PC",
}

GENRE_ALIASES = {
    "action": "Action", "ação": "Action", "acao": "Action",
    "rpg": "RPG",
    "sports": "Sports", "esporte": "Sports", "esportes": "Sports",
    "racing": "Racing", "corrida": "Racing",
    "adventure": "Adventure", "aventura": "Adventure",
    "shooter": "Shooter", "tiro": "Shooter",
    "platform": "Platform",
    "simulation": "Simulation", "simulação": "Simulation", "simulacao": "Simulation",
    "strategy": "Strategy", "estratégia": "Strategy", "estrategia": "Strategy",
    "fighting": "Fighting", "luta": "Fighting",
    "puzzle": "Puzzle",
    "misc": "Misc",
}

def _detect_metric(text: str) -> str:
    t = text.lower()

    # Regional
    if re.search(r"\b(na|north america|américa do norte|america do norte|eua)\b", t):
        return "na_sales"
    if re.search(r"\b(eu|europe|europa)\b", t):
        return "eu_sales"
    if re.search(r"\b(jp|japan|jap[aã]o)\b", t):
        return "jp_sales"

    # Scores
    if re.search(r"\b(metacritic|nota cr[ií]tica|cr[ií]tica|critic score|critic)\b", t):
        return "critic_score"
    if re.search(r"\b(user score|nota de usu[aá]rio|usu[aá]rios|usuarios)\b", t):
        return "user_score"

    # Global sales
    if re.search(r"\b(best[- ]?selling|mais vendidos?|vendas? globais?|sales)\b", t):
        return "global_sales"
    return "global_sales"


def _detect_year(text: str) -> Any:
    years = re.findall(r"\b(19[7-9]\d|20[0-3]\d)\b", text)
    if years:
        try:
            y = int(years[0])
            if 1970 <= y <= 2030:
                return y
        except Exception:
            pass
    return None


def _detect_platform(text: str) -> Any:
    t = text.lower()
    for k, v in PLATFORM_ALIASES.items():
        if re.search(rf"\b{k}\b", t):
            return v
    return None


def _detect_genre(text: str) -> Any:
    t = text.lower()
    for k, v in GENRE_ALIASES.items():
        if re.search(rf"\b{k}\b", t):
            return v
    return None


def _detect_limit(text: str) -> int:
    m = re.search(r"top\D{0,3}(\d{1,3})", text.lower())
    if m:
        try:
            n = int(m.group(1))
            return max(1, min(100, n))
        except Exception:
            pass
    return 10


def _detect_aggregate_term(text: str) -> Any:
    """
    Tenta extrair "franquia/termo" para agregação:
    - "média da franquia Zelda"
    - "average for franchise Mario"
    - "média de nota de Pokemon"
    """
    t = text.lower()

    m = re.search(r"\bfranq[uú]ia\s+([a-z0-9 :\-&]+)", t)
    if not m:
        m = re.search(r"\bfranchise\s+([a-z0-9 :\-&]+)", t)
    if m:
        term = m.group(1).strip(" .?")
        return term if term else None

    m = re.search(r"(m[eé]dia|average|mean)[^a-z0-9]+(de|of)\s+(nota\s+da?\s+|score\s+of\s+)?([a-z0-9 :\-&]+)", t)
    if m:
        term = m.group(4).strip(" .?")
        return term if term else None

    if re.search(r"\bm[eé]dia|average|mean\b", t):
        tokens = re.findall(r"[a-z0-9]+", t)
        stop = set(list(PLATFORM_ALIASES.keys()) + list(GENRE_ALIASES.keys()) +
                   ["top", "vendas", "globais", "sales", "nota", "critica", "crítica",
                    "usuario", "usuário", "users", "score", "em", "no", "na", "de", "do", "da",
                    "franquia", "franchise", "metacritic", "eu", "na", "jp", "europe", "japan"])
        cands = [tok for tok in tokens if tok not in stop and len(tok) > 2]
        if cands:
            return " ".join(cands)

    return None


def parse_question(question: str) -> Dict[str, Any]:
    """
    Parser simples PT/EN -> estrutura para endpoints.
    - Se detectar "média/average" + termo, entra em modo aggregate.
    - Caso contrário, retorna modo rankings.
    """
    text = (question or "").strip()
    lower = text.lower()

    metric = _detect_metric(lower)
    year = _detect_year(lower)
    platform = _detect_platform(lower)
    genre = _detect_genre(lower)
    limit = _detect_limit(lower)

    aggregate_intent = bool(re.search(r"\b(m[eé]dia|average|mean)\b", lower)) or bool(re.search(r"\bfranq[uú]ia|franchise\b", lower))
    name_contains = _detect_aggregate_term(lower) if aggregate_intent else None

    filters: Dict[str, Any] = {}
    if year is not None: filters["year"] = int(year)
    if platform: filters["platform"] = platform
    if genre: filters["genre"] = genre

    if aggregate_intent and name_contains:
        if metric not in ("critic_score", "user_score", "global_sales", "na_sales", "eu_sales", "jp_sales"):
            metric = "critic_score"
        return {
            "mode": "aggregate",
            "metric": metric,
            "filters": filters,
            "name_contains": name_contains,
            "limit": limit,
        }

    return {
        "mode": "rankings",
        "metric": metric,
        "filters": filters,
        "limit": limit,
    }
