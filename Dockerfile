FROM python:3.11-slim

# Imposta le variabili d'ambiente per Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Imposta la directory di lavoro
WORKDIR /app

# Installa le dipendenze di sistema necessarie
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia il file dei requirements e installa le dipendenze usando uv
COPY requirements.txt .
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r requirements.txt

# Crea le cartelle necessarie per i volumi (verranno sovrascritte se montate, ma è buona pratica crearle)
RUN mkdir -p /app/kb /docs

# Copia il codice sorgente
COPY . /app/

# Comando di default per avviare la chat CLI (può essere sovrascritto dal docker-compose)
CMD ["python", "chat.py"]
