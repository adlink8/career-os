FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CAREER_OS_DB_PATH=/app/data/career_jobs.sqlite

COPY bin ./bin
COPY plugins ./plugins
COPY scripts ./scripts
COPY config ./config
COPY knowledge ./knowledge
COPY templates ./templates
COPY README.md AGENTS.md ./

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD ["python", "scripts/docker-healthcheck.py"]

CMD ["python", "bin/career_jobs_cli.py", "stats"]
