FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 OPENBLAS_NUM_THREADS=2
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 app
COPY api ./api
COPY database ./database
COPY dashboard ./dashboard
COPY .streamlit ./.streamlit
COPY docs/evidence/model-selection.json ./docs/evidence/model-selection.json
COPY artifacts/model.joblib ./artifacts/model.joblib
USER app
EXPOSE 8000 8501
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
