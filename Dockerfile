FROM python:3.13-slim

# Usuario no-root por seguridad
RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

COPY requirements.prod.txt .

RUN pip install --no-cache-dir -r requirements.prod.txt

COPY app/ ./app/

# Cambiar ownership y ejecutar como appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
