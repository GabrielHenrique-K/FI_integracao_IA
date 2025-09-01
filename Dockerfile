ARG PYVER=3.11
FROM python:${PYVER}-slim AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gfortran libopenblas-dev ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir --prefer-binary -r requirements.txt

############################
# Target: API (FastAPI)
############################
FROM base AS api
COPY . /app
ENV DATA_PATH=/app/data/base_jogos.csv
EXPOSE 8000
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]

############################
# Target: UI (Streamlit)
############################
FROM base AS ui
COPY . /app
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    API_URL=http://localhost:8000
EXPOSE 8501
CMD ["python","-m","streamlit","run","streamlit_app/Home.py","--server.port","8501","--server.address","0.0.0.0"]
