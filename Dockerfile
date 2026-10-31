FROM python:3.13-slim-trixie AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd -g 10001 secticket \
    && useradd -m -u 10001 -g secticket \
       -s /usr/sbin/nologin secticket \
    && mkdir -p /app/data \
    && chown secticket:secticket /app/data

COPY --chown=secticket:secticket app/ ./app/
COPY --chown=secticket:secticket migrations/ ./migrations/
COPY --chown=secticket:secticket \
    docker/entrypoint.sh /usr/local/bin/secticket-entrypoint

RUN chmod 755 /usr/local/bin/secticket-entrypoint

USER secticket

EXPOSE 5000

ENTRYPOINT ["/usr/local/bin/secticket-entrypoint"]

CMD ["gunicorn", "--workers", "2", \
     "--bind", "0.0.0.0:5000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:create_app()"]


# Production runtime without pip and its vendored libraries
FROM base AS runtime

USER root
RUN python -m pip uninstall --yes pip
USER secticket


# Test environment - not included in production image
FROM base AS test

USER root

COPY requirements-dev.txt ./requirements-dev.txt

RUN pip install --no-cache-dir -r requirements-dev.txt

COPY --chown=secticket:secticket tests/ ./tests/

USER secticket

ENTRYPOINT []

CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"]
