FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system upexnote && adduser --system --ingroup upexnote upexnote

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY --chown=upexnote:upexnote app ./app

USER upexnote
EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--forwarded-allow-ips=*", "--port", "8000"]
