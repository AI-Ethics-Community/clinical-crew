# Guía de Deployment en Producción (Render)

Esta guía explica cómo desplegar Clinical Crew en producción usando Render, incluyendo la configuración del sistema RAG.

## Arquitectura en Producción

```
┌─────────────────────────────────────────────────────┐
│                   Render Web Service                 │
│  ┌─────────────────────────────────────────────┐   │
│  │  FastAPI App                                 │   │
│  │  ┌──────────────┐     ┌──────────────┐     │   │
│  │  │ ChromaDB     │     │ MongoDB      │     │   │
│  │  │ (local disk) │     │ (Render DB)  │     │   │
│  │  └──────────────┘     └──────────────┘     │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  📦 Vectorstore: Backup comprimido en repo          │
│  📄 PDFs: Google Cloud Storage (free tier)          │
└─────────────────────────────────────────────────────┘
```

## Paso 1: Preparar el Vectorstore

### 1.1 Hacer backup del vectorstore actual

```bash
# Ejecutar script de backup
./scripts/backup_vectorstore.sh
```

Esto genera:
- `vectorstore-backup.tar.gz` (~200KB)
- `vectorstore-backup.tar.gz.sha256` (checksum)

### 1.2 Incluir backup en Git (Opción A - Recomendada si <1MB)

```bash
# Verificar que sea pequeño
ls -lh vectorstore-backup.tar.gz

# Si es < 1MB, incluirlo en Git
git add vectorstore-backup.tar.gz vectorstore-backup.tar.gz.sha256
git commit -m "feat: add vectorstore backup for production deployment"
```

### 1.3 Subir a Google Cloud Storage (Opción B - Si el backup es grande)

```bash
# Instalar gcloud CLI si no lo tienes
# https://cloud.google.com/sdk/docs/install

# Autenticarse
gcloud auth login

# Crear bucket (free tier: 5GB)
gsutil mb -l us-central1 gs://clinical-crew-vectorstore

# Hacer público el archivo
gsutil cp vectorstore-backup.tar.gz gs://clinical-crew-vectorstore/
gsutil acl ch -u AllUsers:R gs://clinical-crew-vectorstore/vectorstore-backup.tar.gz

# Obtener URL pública
echo "https://storage.googleapis.com/clinical-crew-vectorstore/vectorstore-backup.tar.gz"
```

## Paso 2: Preparar los PDFs (Base de Conocimiento)

### Opción A: Subir a Google Cloud Storage (Recomendada)

```bash
# Crear estructura por especialidad
gsutil mb -l us-central1 gs://clinical-crew-knowledge-base

# Subir PDFs organizados por especialidad
gsutil -m cp data/knowledge_base/cardiology/*.pdf gs://clinical-crew-knowledge-base/cardiology/
gsutil -m cp data/knowledge_base/endocrinology/*.pdf gs://clinical-crew-knowledge-base/endocrinology/
gsutil -m cp data/knowledge_base/pharmacology/*.pdf gs://clinical-crew-knowledge-base/pharmacology/

# Hacer públicos (solo lectura)
gsutil -m acl ch -r -u AllUsers:R gs://clinical-crew-knowledge-base/
```

### Opción B: Indexar manualmente en producción

Subir PDFs una sola vez usando el endpoint de administración (implementar si es necesario).

## Paso 3: Configurar Render

### 3.1 Crear MongoDB Database en Render

1. Dashboard → New → PostgreSQL/MongoDB
2. Seleccionar **MongoDB**
3. Plan: **Starter** ($7/mes) o **Free** (30 días)
4. Región: **Oregon (us-west)**
5. Database name: `hacknation_medical`
6. Copiar **Internal Connection String**

### 3.2 Crear Web Service en Render

1. Dashboard → New → Web Service
2. Conectar repositorio de GitHub
3. Configuración:

```yaml
Name: clinical-crew-api
Region: Oregon
Branch: main
Runtime: Docker
Instance Type: Starter ($7/mes) o Free

# Build Command (automático con Dockerfile)
# Docker Command (automático - usa start.sh)
```

### 3.3 Configurar Variables de Entorno

En Render Dashboard → Environment:

```bash
# ============================================================================
# REQUERIDAS
# ============================================================================
GEMINI_API_KEY=tu_clave_aquí
PUBMED_EMAIL=tu_email@ejemplo.com

# MongoDB (copiar de Render Database)
MONGODB_URL=mongodb://user:pass@host:port/hacknation_medical

# ============================================================================
# CONFIGURACIÓN RAG
# ============================================================================

# Si usaste Opción B (GCS) para el vectorstore:
GCS_VECTORSTORE_URL=https://storage.googleapis.com/clinical-crew-vectorstore/vectorstore-backup.tar.gz

# Si usaste GCS para los PDFs (Opción A):
# Formato: specialty:filename:url,specialty:filename:url,...
GCS_KNOWLEDGE_BASE_FILES=cardiology:guia_cardiologia.pdf:https://storage.googleapis.com/.../cardiology/guia_cardiologia.pdf,endocrinology:guia_endocrinologia.pdf:https://storage.googleapis.com/.../endocrinology/guia_endocrinologia.pdf

# Solo si quieres forzar reindexación en cada deploy (NO RECOMENDADO)
REINDEX_ON_START=false

# ============================================================================
# OPCIONALES
# ============================================================================
PUBMED_API_KEY=tu_api_key_ncbi  # Para mayor rate limit
GEMINI_PRO_MODEL=gemini-2.5-pro-latest
GEMINI_FLASH_MODEL=gemini-2.5-flash-latest
GEMINI_TEMPERATURE=0.05
RAG_MIN_RELEVANCE_SCORE=0.3
RAG_TOP_K=5
CORS_ORIGINS=https://tu-frontend.com,https://www.tu-frontend.com
DEBUG=false
LOG_LEVEL=INFO
```

### 3.4 Configurar Persistent Disk (Opcional)

Para mantener el vectorstore entre deployments:

1. Render Dashboard → Service → Settings
2. Persistent Disks → Add Disk
3. Mount Path: `/app/data/vectorstore`
4. Size: 1 GB (suficiente)

**Nota**: Con el backup incluido en Git, esto no es necesario.

## Paso 4: Deploy

```bash
# Commit cambios
git add .
git commit -m "feat: configure production deployment for Render"
git push origin main
```

Render detectará el push y desplegará automáticamente.

## Paso 5: Verificar el Deployment

### 5.1 Revisar logs

```
Render Dashboard → Service → Logs
```

Deberías ver:
```
🚀 Starting Clinical Crew API...
🔍 Checking vectorstore...
📦 Vectorstore vacío, restaurando...
✅ Vectorstore restaurado exitosamente
🎯 Starting FastAPI server on port 8000...
```

### 5.2 Health check

```bash
# Usar la URL de Render
curl https://clinical-crew-api.onrender.com/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "service": "Clinical Crew API",
  "database": "connected",
  "vectorstore": "ready"
}
```

### 5.3 Verificar especialistas

```bash
curl https://clinical-crew-api.onrender.com/api/v1/especialistas
```

## Actualización del RAG (Poco Frecuente)

### Actualizar Vectorstore

```bash
# 1. Hacer cambios locales (agregar PDFs, reindexar)
python -m app.rag.document_indexer --all

# 2. Crear nuevo backup
./scripts/backup_vectorstore.sh

# 3. Commit y push
git add vectorstore-backup.tar.gz vectorstore-backup.tar.gz.sha256
git commit -m "chore: update vectorstore with new documents"
git push origin main

# Render redesplegará automáticamente
```

### Agregar nuevos PDFs sin redeployar

Si configuraste `GCS_KNOWLEDGE_BASE_FILES`:

1. Sube PDF a Google Cloud Storage
2. Agrega URL a la variable de entorno en Render
3. Manual restart del servicio (Render Dashboard → Manual Deploy)

## Costos Estimados (Render)

- **Web Service Starter**: $7/mes (512MB RAM, 0.5 CPU)
- **MongoDB Starter**: $7/mes (512MB RAM, 1GB storage)
- **Persistent Disk**: $0.25/GB/mes (opcional)
- **Total**: ~$14-15/mes

**Alternativa Free Tier**:
- Web Service Free + MongoDB Free = $0/mes
- Limitaciones: sleep después de inactividad, 100GB bandwidth/mes

## Solución de Problemas

### Error: "vectorstore-backup.tar.gz no encontrado"

**Solución**: Incluye el backup en Git o configura `GCS_VECTORSTORE_URL`.

### Error: "GEMINI_API_KEY environment variable is required"

**Solución**: Configura todas las variables requeridas en Render Environment.

### Error: "No documents found in vectorstore"

**Solución**:
1. Verifica que el backup fue restaurado: `ls data/vectorstore/`
2. Verifica logs de inicio
3. Configura `REINDEX_ON_START=true` temporalmente

### Servicio lento o con timeouts

**Solución**:
- Upgrade a plan Starter (mínimo recomendado)
- Reduce workers en start.sh (actualmente 2)
- Optimiza RAG_TOP_K (actualmente 5)

## Monitoring y Logs

### Logs en tiempo real

```bash
# Render CLI
render logs -f -s clinical-crew-api
```

### Métricas importantes

- Response time /api/v1/consultation
- ChromaDB query performance
- MongoDB connection pool
- PubMed API rate limits

## Referencias

- [Render Documentation](https://render.com/docs)
- [Google Cloud Storage Free Tier](https://cloud.google.com/free)
- [ChromaDB Production Guide](https://docs.trychroma.com/deployment)
