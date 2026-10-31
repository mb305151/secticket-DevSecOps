FROM python:3.13-slim-trixie

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

USER secticket

EXPOSE 5000

CMD ["gunicorn", "--workers", "2", \
     "--bind", "0.0.0.0:5000", \
     "--access-logfile", "-", \
     "app:create_app()"]
