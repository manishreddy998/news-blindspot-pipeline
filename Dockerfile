FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so code edits don't redo this slow layer.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install -e ".[bigquery,dbt,orchestration,dashboard,dev]" \
    && dagster --version && streamlit --version && dbt --version

COPY . .

ENV DAGSTER_HOME=/app/data/dagster DBT_PROJECT_DIR=/app/dbt
EXPOSE 3000 8501

# Credentials are mounted at run time, never baked into the image.
CMD ["python", "-m", "blindspot.ingest.load_gdelt", "--hours", "24"]
