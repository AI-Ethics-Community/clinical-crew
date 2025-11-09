FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar scripts de setup
COPY ./scripts ./scripts
RUN chmod +x scripts/*.sh scripts/*.py

# Copiar configuración y archivos de aplicación
COPY ./app ./app
COPY ./data ./data

# Copiar backup de vectorstore si existe
COPY vectorstore-backup.tar.g[z] ./ 2>/dev/null || true
COPY vectorstore-backup.tar.gz.sha25[6] ./ 2>/dev/null || true

# Crear directorios necesarios
RUN mkdir -p /app/logs && \
    mkdir -p /app/data/vectorstore && \
    chmod -R 755 /app/data

# Exponer puerto (Render asigna dinámicamente, pero documentamos el default)
EXPOSE 8000

# Variables de entorno por defecto
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

# Script de inicio
COPY start.sh .
RUN chmod +x start.sh

# Comando por defecto - usa el puerto de Render
CMD ["./start.sh"]
