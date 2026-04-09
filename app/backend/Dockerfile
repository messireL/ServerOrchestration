FROM python:3.12-slim

LABEL org.opencontainers.image.title="ServerOrchestration Backend" \
      org.opencontainers.image.description="Backend API for ServerOrchestration" \
      org.opencontainers.image.source="https://github.com/messireL/ServerOrchestration"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home --home-dir ${APP_HOME} app

COPY requirements.txt ${APP_HOME}/requirements.txt
RUN pip install --upgrade pip && pip install -r ${APP_HOME}/requirements.txt

COPY src ${APP_HOME}/src
RUN chown -R app:app ${APP_HOME}

USER app

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
