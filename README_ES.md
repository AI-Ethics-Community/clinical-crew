# Sistema de Interconsulta Médica con IA Multi-Agente

Sistema inteligente que simula el proceso de interconsulta médica utilizando múltiples agentes especializados de IA, cada uno con acceso a bases de conocimiento especializadas mediante RAG, búsqueda en literatura científica y razonamiento basado en evidencia.

## Descripción General

Este sistema recrea la interacción entre profesionales de la salud mediante agentes de IA especializados, permitiendo una atención médica más integral y fundamentada en evidencia científica.

### Flujo de Trabajo Médico Tradicional

1. **Consulta Inicial**: Un paciente es atendido por un médico general
2. **Evaluación**: El médico analiza si puede resolver el caso o necesita apoyo
3. **Interconsulta**: Si requiere, genera notas de interconsulta a especialistas
4. **Respuesta Especializada**: Cada especialista analiza y responde con su expertise
5. **Integración**: El médico general integra las respuestas y genera un plan

### Flujo del Sistema IA

![Diagrama de Flujo de Clinical Crew](public/images/diagrams/clinical-crew-diagram.png)

El sistema implementa un flujo de trabajo multi-agente sofisticado usando LangGraph:

1. **Fase de Interrogación**: El médico general recopila información necesaria del paciente
2. **Evaluación**: Determina si es posible una respuesta directa o si se necesitan especialistas
3. **Ejecución Paralela de Especialistas**: Múltiples especialistas analizan el caso simultáneamente
4. **Integración**: El médico general sintetiza todas las respuestas en un expediente clínico completo

#### Arquitectura LangGraph

![Diagrama Nativo de LangGraph](public/images/diagrams/graph_native.png)

**Estructura de Nodos**:

- `__start__` → Punto de entrada
- `interrogate` → Recopilación de información del paciente
- `evaluate` → Evaluación de complejidad del caso
- `direct_response` → Casos simples (el MG responde directamente)
- `generate_interconsultations` → Crear notas de interconsulta para especialistas
- `execute_specialists` → ⚡ **Ejecución paralela** de agentes especialistas
- `integrate` → Sintetizar todas las respuestas de especialistas
- `__end__` → Finalización del flujo

**Tipos de Aristas**:

- Líneas sólidas (→): Transiciones directas
- Líneas punteadas (⋯→): Transiciones condicionales basadas en evaluación

## Características Principales

### 🤖 Sistema Multi-Agente con LangGraph

- **Agente Médico General**: Enrutador inteligente que evalúa consultas y coordina especialistas
- **Agentes Especialistas**: Cada uno con conocimiento profundo en su área
- **Ejecución Paralela**: Múltiples interconsultas simultáneas
- **Flujo Dinámico**: Manejo de ciclos para solicitar información adicional

### 📚 RAG (Retrieval Augmented Generation)

- Base de conocimiento especializada por área médica
- Búsqueda semántica en documentos clínicos
- Embeddings con Google Gemini
- Vector store con ChromaDB

### 🔬 Integración con Literatura Científica

- Búsqueda en PubMed/NCBI
- Acceso a guías de práctica clínica
- Respuestas basadas en evidencia científica

### 📋 Sistema de Notas Médicas

- **Nota de Interconsulta**: Contexto, pregunta específica y expectativas
- **Nota de Contrarreferencia**: Evaluación, razonamiento y respuesta basada en evidencia
- **Expediente Clínico**: Formato estructurado con todas las interacciones

### 🏗️ Arquitectura Extensible

- Fácil adición de nuevos especialistas
- Configuración basada en archivos
- Sistema de plugins para herramientas específicas

## Arquitectura Técnica

### Stack Tecnológico

```
Backend
├── FastAPI              # Framework web asíncrono
├── LangGraph            # Orquestación de agentes
├── Google Gemini        # LLM (2.5 Pro/Flash)
├── LangChain            # Componentes RAG y agentes
├── ChromaDB             # Vector store
├── MongoDB              # Persistencia de datos
└── NCBI E-utilities     # API de PubMed
```

### Componentes del Sistema

#### 1. API Layer (FastAPI)

```python
POST   /api/v1/consulta                    # Iniciar consulta médica
POST   /api/v1/consulta/{id}/responder     # Agregar información adicional
GET    /api/v1/consulta/{id}               # Obtener expediente completo
GET    /api/v1/consulta/{id}/estado        # Estado del flujo
WS     /api/v1/consulta/{id}/stream        # WebSocket para streaming
```

#### 2. Agent Layer (LangGraph)

```
Estado del Grafo:
├── consulta_original      # Pregunta del usuario
├── contexto_paciente      # Información del caso
├── evaluacion_general     # Análisis del médico general
├── interconsultas[]       # Lista de interconsultas generadas
├── contrarreferencias[]   # Respuestas de especialistas
├── preguntas_pendientes[] # Info adicional requerida
└── respuesta_final        # Integración final

Nodos:
├── medico_general_evaluacion    # Evalúa si puede responder o interconsultar
├── generar_interconsultas       # Crea notas de interconsulta
├── ejecutar_especialistas       # Ejecuta agentes en paralelo
├── verificar_preguntas          # Revisa si hay info pendiente
├── integrar_respuestas          # Genera expediente final
└── solicitar_informacion        # Espera input del usuario
```

#### 3. RAG System

```
Document Pipeline:
1. Indexación de documentos por especialidad
2. Chunking semántico
3. Generación de embeddings (Gemini Embeddings)
4. Almacenamiento en ChromaDB
5. Búsqueda semántica híbrida (vector + keyword)
```

#### 4. Database Schema (MongoDB)

```javascript
// Consulta médica
{
  _id: ObjectId,
  usuario_id: String,
  consulta_original: String,
  contexto_paciente: Object,
  estado: "evaluando" | "interconsultando" | "esperando_info" | "completado",
  timestamp: DateTime,

  // Flujo de trabajo
  evaluacion_general: {
    puede_responder_directo: Boolean,
    especialistas_requeridos: [String],
    razonamiento: String
  },

  // Interconsultas
  interconsultas: [{
    especialidad: String,
    pregunta_especifica: String,
    contexto_relevante: Object,
    timestamp: DateTime
  }],

  // Contrarreferencias
  contrarreferencias: [{
    especialidad: String,
    evaluacion: String,
    evidencia_utilizada: [String],
    respuesta: String,
    requiere_info_adicional: Boolean,
    preguntas: [String],
    timestamp: DateTime
  }],

  // Expediente final
  expediente: {
    resumen_general: String,
    notas_completas: String,
    respuesta_final: String,
    timestamp: DateTime
  }
}
```

## Estructura del Proyecto

```
clinical-crew/
├── app/
│   ├── __init__.py
│   ├── main.py                          # Aplicación FastAPI
│   │
│   ├── api/                             # Endpoints
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── consultations.py        # Endpoints de consultas
│   │   │   └── websockets.py           # WebSocket handlers
│   │   └── dependencies.py             # Dependencias compartidas
│   │
│   ├── agents/                          # Sistema de agentes LangGraph
│   │   ├── __init__.py
│   │   ├── graph.py                    # Definición del grafo principal
│   │   ├── general_practitioner.py     # Agente coordinador
│   │   ├── specialists/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Clase base para especialistas
│   │   │   ├── cardiology.py
│   │   │   ├── endocrinology.py
│   │   │   └── pharmacology.py
│   │   └── prompts/                    # Plantillas de prompts
│   │       ├── general_practitioner.py
│   │       └── specialists.py
│   │
│   ├── models/                          # Modelos de datos
│   │   ├── __init__.py
│   │   ├── consultation.py             # Modelos Pydantic
│   │   ├── notes.py                    # Modelos de notas médicas
│   │   └── database.py                 # Modelos MongoDB (Beanie)
│   │
│   ├── rag/                             # Sistema RAG
│   │   ├── __init__.py
│   │   ├── vector_store.py             # ChromaDB wrapper
│   │   ├── embeddings.py               # Gemini embeddings
│   │   ├── document_indexer.py         # Indexación de documentos
│   │   └── retriever.py                # Búsqueda semántica
│   │
│   ├── services/                        # Servicios externos
│   │   ├── __init__.py
│   │   ├── gemini_client.py            # Cliente de Google Gemini
│   │   ├── pubmed_client.py            # Cliente de PubMed
│   │   └── notes_service.py            # Generación de notas médicas
│   │
│   └── config/                          # Configuración
│       ├── __init__.py
│       ├── settings.py                 # Pydantic Settings
│       └── specialists.yaml            # Configuración de especialistas
│
├── data/                                # Datos y documentos
│   ├── knowledge_base/                 # Base de conocimiento
│   │   ├── cardiology/
│   │   ├── endocrinology/
│   │   └── pharmacology/
│   └── vectorstore/                    # Almacenamiento de ChromaDB
│
├── tests/                               # Tests
│   ├── __init__.py
│   ├── test_agents/
│   ├── test_api/
│   └── test_rag/
│
├── docs/                                # Documentación adicional
│   ├── api_examples.md
│   ├── adding_specialists.md
│   └── medical_notes_format.md
│
├── .env.example                         # Variables de entorno ejemplo
├── .gitignore
├── docker-compose.yml                   # Docker services
├── Dockerfile                           # Container de la app
├── requirements.txt                     # Dependencias Python
├── pyproject.toml                       # Configuración del proyecto
└── README.md
```

## Instalación y Configuración

### Requisitos Previos

- Python 3.11+ (recomendado 3.13)
- Docker (MongoDB se levanta automáticamente, no necesitas Docker Compose si ya tienes MongoDB corriendo)
- API Key de Google Gemini
- Cuenta de NCBI (para PubMed API - opcional)

### Opción 1: Quick Start (Recomendado)

El script `quickstart.sh` configura automáticamente todo el entorno:

```bash
# Da permisos de ejecución y ejecuta
chmod +x quickstart.sh
./quickstart.sh
```

Este script:

- ✅ Verifica Python 3.11+
- ✅ Crea el entorno virtual
- ✅ Instala todas las dependencias
- ✅ Copia `.env.example` a `.env`
- ✅ Levanta MongoDB con Docker
- ✅ Crea directorios necesarios

**Importante:** Después de ejecutar el script, edita `.env` y agrega tu `GEMINI_API_KEY` y `PUBMED_EMAIL`.

### Opción 2: Instalación Manual

#### Paso 1: Clonar el Repositorio

```bash
git clone https://github.com/AI-Ethics-Community/clinical-crew.git
cd clinical-crew
```

#### Paso 2: Configurar Variables de Entorno

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales (mínimo requerido):

```bash
# REQUERIDO: Google Gemini API Key
GEMINI_API_KEY=tu_api_key_aqui

# REQUERIDO: Email para PubMed API
PUBMED_EMAIL=dc.lerma@ugto.mx

# Opcional: NCBI API Key para rate limits más altos
PUBMED_API_KEY=tu_ncbi_api_key

# El resto de valores tienen defaults adecuados
```

#### Paso 3: Instalar Dependencias

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

**Nota:** Si tienes conflictos de dependencias, el archivo `requirements.txt` ya está configurado con versiones compatibles.

#### Paso 4: Iniciar MongoDB

```bash
# Si tienes Docker instalado
docker run -d -p 27017:27017 --name hacknation_mongodb mongo:7.0

# O si ya tienes MongoDB instalado localmente, solo asegúrate que esté corriendo
```

#### Paso 5: Ejecutar la Aplicación

```bash
# Desarrollo con auto-reload
python3 -m app.main

# O usando uvicorn directamente
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verificar Instalación

La API estará disponible en: `http://localhost:8000`

```bash
# Verificar health check
curl http://localhost:8000/health

# Acceder a la documentación interactiva
open http://localhost:8000/docs  # o visita en tu navegador
```

### Índice de Base de Conocimiento (Opcional)

Si quieres usar el sistema RAG con documentos personalizados:

```bash
# Indexar todos los documentos
python -m app.rag.document_indexer --all

# Indexar especialidad específica
python -m app.rag.document_indexer --specialty cardiology
```

**Nota:** El sistema funciona sin documentos indexados, utilizando solo el conocimiento de los LLMs y PubMed.

Documentación interactiva: `http://localhost:8000/docs`

## Uso de la API

### Ejemplo 1: Consulta Simple

```bash
curl -X POST "http://localhost:8000/api/v1/consulta" \
  -H "Content-Type: application/json" \
  -d '{
    "consulta": "Paciente masculino de 45 años con diabetes tipo 2 descompensada. ¿Puedo iniciar sertralina para depresión?",
    "contexto": {
      "edad": 45,
      "sexo": "masculino",
      "diagnosticos": ["Diabetes Mellitus tipo 2", "Depresión"],
      "medicamentos_actuales": ["Metformina 850mg c/12h", "Glibenclamida 5mg c/24h"],
      "alergias": []
    }
  }'
```

Respuesta:

```json
{
  "consulta_id": "507f1f77bcf86cd799439011",
  "estado": "procesando",
  "mensaje": "Consulta recibida. El médico general está evaluando el caso."
}
```

### Ejemplo 2: Obtener Expediente Completo

```bash
curl -X GET "http://localhost:8000/api/v1/consulta/507f1f77bcf86cd799439011"
```

Respuesta (cuando está completo):

```json
{
  "consulta_id": "507f1f77bcf86cd799439011",
  "estado": "completado",
  "expediente": {
    "nota_inicial": {
      "tipo": "Evaluación Médico General",
      "timestamp": "2025-11-08T10:30:00Z",
      "contenido": "Paciente con diabetes tipo 2 descompensada que requiere inicio de antidepresivo. Requiero interconsulta con Endocrinología para optimización de control glucémico y Farmacología para evaluar interacciones medicamentosas.",
      "decision": "interconsultar",
      "especialistas_solicitados": ["Endocrinología", "Farmacología"]
    },

    "interconsultas": [
      {
        "especialidad": "Endocrinología",
        "timestamp": "2025-11-08T10:30:05Z",
        "nota": "Motivo de interconsulta: Optimización de control glucémico en paciente que iniciará antidepresivo.\n\nAntecedentes: Diabetes tipo 2 descompensada.\n\nMedicación actual: Metformina 850mg c/12h, Glibenclamida 5mg c/24h.\n\nPregunta específica: ¿Requiere ajuste de esquema antes de iniciar ISRS?"
      },
      {
        "especialidad": "Farmacología",
        "timestamp": "2025-11-08T10:30:05Z",
        "nota": "Motivo de interconsulta: Evaluación de seguridad farmacológica.\n\nMedicación propuesta: Sertralina.\n\nMedicación actual: Metformina 850mg c/12h, Glibenclamida 5mg c/24h.\n\nPregunta específica: ¿Existen interacciones significativas? ¿Requiere ajuste de dosis?"
      }
    ],

    "contrarreferencias": [
      {
        "especialidad": "Endocrinología",
        "timestamp": "2025-11-08T10:31:20Z",
        "evaluacion": "Revisión de esquema antidiabético en paciente que iniciará ISRS.",
        "evidencia": [
          "ADA Standards of Medical Care in Diabetes 2024",
          "PMID: 34561234 - ISRS effects on glycemic control"
        ],
        "respuesta": "RECOMENDACIONES:\n\n1. El esquema actual (Metformina + Glibenclamida) es adecuado para iniciar ISRS.\n\n2. PRECAUCIÓN: Los ISRS pueden afectar el control glucémico:\n   - Sertralina puede causar hiperglucemia en fase inicial\n   - Posteriormente puede mejorar la glucemia (efecto dual)\n\n3. MONITOREO RECOMENDADO:\n   - Glucemia capilar 3 veces al día durante 2 semanas\n   - HbA1c de control en 3 meses\n   - Ajustar hipoglucemiantes según evolución\n\n4. No requiere modificación preventiva del esquema antidiabético.\n\nREFERENCIAS: ADA 2024 Guidelines, Diabetes Care 2023;46(Suppl.1)."
      },
      {
        "especialidad": "Farmacología",
        "timestamp": "2025-11-08T10:31:45Z",
        "evaluacion": "Análisis de interacciones medicamentosas Sertralina con esquema antidiabético.",
        "evidencia": [
          "Micromedex Drug Interactions Database",
          "PMID: 28765432 - Sertralina safety in diabetes",
          "FDA Prescribing Information - Sertralina"
        ],
        "respuesta": "ANÁLISIS DE INTERACCIONES:\n\n1. SERTRALINA + METFORMINA:\n   - No interacción significativa\n   - Seguro combinar\n\n2. SERTRALINA + GLIBENCLAMIDA:\n   - Interacción de SEVERIDAD MODERADA\n   - Mecanismo: Ambos metabolizados por CYP2C9\n   - Riesgo: Posible aumento de concentración de glibenclamida → mayor riesgo de hipoglucemia\n\n3. RECOMENDACIONES:\n   a) DOSIS INICIAL: Sertralina 25-50mg/día\n   b) TITULACIÓN: Incremento gradual según respuesta\n   c) MONITOREO: Vigilar síntomas de hipoglucemia\n   d) EDUCACIÓN: Signos de alarma de hipoglucemia\n   e) Considerar cambio a Metformina + iDPP4 si hipoglucemias frecuentes\n\n4. CONTRAINDICACIONES: Ninguna absoluta.\n\nCONCLUSIÓN: PUEDE INICIARSE con precauciones mencionadas.\n\nREFERENCIAS: Micromedex 2025, Drug Interact Facts 2025."
      }
    ],

    "respuesta_final": {
      "timestamp": "2025-11-08T10:32:00Z",
      "contenido": "INTEGRACIÓN DE INTERCONSULTAS\n\nPaciente masculino 45 años con DM2 + Depresión.\n\nCONSULTA: ¿Puede iniciarse Sertralina?\n\nRESPUESTA: SÍ, PUEDE INICIARSE CON PRECAUCIONES.\n\nFUNDAMENTACIÓN:\n\n1. SEGURIDAD ENDOCRINA (Endocrinología):\n   - Esquema antidiabético actual es adecuado\n   - No requiere ajuste preventivo\n   - Monitoreo glucémico estrecho recomendado\n\n2. SEGURIDAD FARMACOLÓGICA (Farmacología):\n   - Interacción Sertralina-Glibenclamida: MODERADA\n   - Riesgo principal: Hipoglucemia\n   - Manejo: Dosis inicial baja, titulación gradual, monitoreo\n\nPLAN TERAPÉUTICO RECOMENDADO:\n\n1. INICIAR: Sertralina 25-50mg en la mañana\n2. TITULAR: Incremento de 25-50mg cada 2 semanas según respuesta (máx 200mg)\n3. MONITOREO:\n   - Glucemia capilar 3 veces/día x 2 semanas\n   - Citas semanales primeras 2 semanas\n   - Evaluar respuesta antidepresiva en 4-6 semanas\n4. EDUCACIÓN:\n   - Signos de hipoglucemia\n   - Continuar medicamentos antidiabéticos\n   - Llevar registro glucémico\n\nCRITERIOS DE DERIVACIÓN:\n- Hipoglucemias frecuentes → revaluar esquema antidiabético\n- No respuesta a Sertralina en 8 semanas → Psiquiatría\n\nNIVEL DE EVIDENCIA: Alto (Guías ADA 2024, Micromedex, revisiones sistemáticas).\n\nSEGUIMIENTO: 1 semana."
    }
  }
}
```

### Ejemplo 3: Agregar Información Adicional

Si un especialista requiere más datos:

```bash
curl -X POST "http://localhost:8000/api/v1/consulta/507f1f77bcf86cd799439011/responder" \
  -H "Content-Type: application/json" \
  -d '{
    "informacion_adicional": {
      "creatinina": "1.2 mg/dL",
      "hba1c": "8.5%",
      "presion_arterial": "140/90 mmHg"
    }
  }'
```

## Formato de Notas Médicas

### Nota de Interconsulta

Estructura estándar que el médico general envía al especialista:

```
NOTA DE INTERCONSULTA A [ESPECIALIDAD]

MOTIVO DE INTERCONSULTA:
[Razón específica de la consulta]

ANTECEDENTES RELEVANTES:
[Información pertinente del caso]

CONTEXTO CLÍNICO:
[Situación actual del paciente]

PREGUNTA ESPECÍFICA:
[Qué se espera que el especialista responda]

INFORMACIÓN RELEVANTE:
[Datos clínicos, laboratorios, medicamentos, etc.]

EXPECTATIVA:
[Qué tipo de orientación se busca]
```

### Nota de Contrarreferencia

Estructura de respuesta del especialista:

```
NOTA DE CONTRARREFERENCIA - [ESPECIALIDAD]

EVALUACIÓN:
[Análisis del caso desde la perspectiva especializada]

REVISIÓN DE EVIDENCIA:
[Fuentes consultadas: guías, artículos, bases de conocimiento]

Referencias utilizadas:
- [Guía/Artículo 1]
- [PMID: xxxxx]
- [Base de datos consultada]

RAZONAMIENTO CLÍNICO:
[Proceso de pensamiento y criterios aplicados]

RESPUESTA A LA PREGUNTA:
[Respuesta clara y específica basada en evidencia]

RECOMENDACIONES:
1. [Recomendación 1]
2. [Recomendación 2]
...

NIVEL DE EVIDENCIA:
[Calidad de la evidencia utilizada]

INFORMACIÓN ADICIONAL REQUERIDA (si aplica):
- [Dato 1 que se necesita]
- [Dato 2 que se necesita]
```

## Arquitectura de Agentes

### Agente Médico General

**Responsabilidades:**

- Recibir y analizar la consulta inicial
- Evaluar complejidad del caso
- Decidir si puede responder directamente o necesita interconsultar
- Seleccionar especialistas apropiados
- Generar notas de interconsulta contextualizadas
- Integrar contrarreferencias
- Generar expediente final

**Herramientas:**

- Conocimiento médico general (RAG)
- Capacidad de razonamiento clínico
- Generación de notas médicas

**Modelo LLM:** Gemini 2.5 Pro

### Agentes Especialistas

Cada especialista tiene la misma estructura base pero con configuración específica:

**Responsabilidades:**

- Recibir nota de interconsulta
- Analizar pregunta y contexto
- Buscar evidencia en su base de conocimiento (RAG)
- Consultar literatura científica (PubMed) si es necesario
- Razonar basándose en guías y evidencia
- Generar contrarreferencia estructurada
- Solicitar información adicional si es insuficiente

**Herramientas:**

- RAG especializado (documentos de su área)
- Búsqueda en PubMed
- Criterios diagnósticos específicos
- Guías de práctica clínica

**Modelo LLM:** Gemini 2.5 Flash (más rápido para especialistas en paralelo)

### Especialistas Iniciales

1. **Cardiología**

   - Enfermedades cardiovasculares
   - Criterios diagnósticos
   - Guías ACC/AHA

2. **Endocrinología**

   - Diabetes, tiroides, trastornos hormonales
   - Guías ADA, Endocrine Society

3. **Farmacología**
   - Interacciones medicamentosas
   - Dosis, contraindicaciones
   - Bases: Micromedex, FDA

## Agregar Nuevos Especialistas

El sistema está diseñado para extensibilidad fácil:

### Paso 1: Agregar Configuración

Editar `app/config/specialists.yaml`:

```yaml
specialists:
  neurology:
    name: "Neurology"
    description: "Specialist in nervous system diseases"
    model: "gemini-2.5-flash-latest"
    rag_collection: "neurology_kb"
    tools:
      - pubmed_search
      - diagnostic_criteria
    custom_prompt: |
      You are an expert neurologist specialized in...
      Your approach should be based on...
```

### Paso 2: Agregar Base de Conocimiento

```bash
# Colocar documentos en:
data/knowledge_base/neurology/
  ├── stroke_guideline.pdf
  ├── epilepsy_criteria.pdf
  └── ...

# Indexar
python -m app.rag.document_indexer --specialty neurology
```

### Paso 3: (Opcional) Crear Clase Especializada

Si requiere lógica específica, crear `app/agents/specialists/neurology.py`:

```python
from app.agents.specialists.base import SpecialistBase

class NeurologySpecialist(SpecialistBase):
    def __init__(self):
        super().__init__(specialty="neurology")

    def additional_tools(self):
        # Herramientas específicas de neurología
        return [self.nihss_scale, self.epilepsy_criteria]
```

El sistema automáticamente detectará y usará el nuevo especialista.

## Tecnologías y Dependencias Principales

```python
# LLM y Agents
langchain>=0.3.0
langgraph>=0.3.0
google-generativeai>=0.8.0

# Web Framework
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
websockets>=13.0

# Database
motor>=3.6.0          # MongoDB async driver
beanie>=1.26.0        # ODM para MongoDB

# RAG
chromadb>=0.5.0
sentence-transformers>=3.0.0

# External APIs
biopython>=1.84       # PubMed/Entrez
httpx>=0.27.0

# Utilities
pydantic>=2.9.0
pydantic-settings>=2.5.0
python-dotenv>=1.0.0
pyyaml>=6.0
```

## Variables de Entorno Completas

```bash
# =============================================================================
# GOOGLE GEMINI CONFIGURATION
# =============================================================================
GEMINI_API_KEY=your_api_key_here
GEMINI_PRO_MODEL=gemini-2.5-pro-latest
GEMINI_FLASH_MODEL=gemini-2.5-flash-latest
GEMINI_TEMPERATURE=0.1              # Baja temperatura para consistencia médica
GEMINI_MAX_OUTPUT_TOKENS=8192

# =============================================================================
# DATABASE CONFIGURATION (MongoDB)
# =============================================================================
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=hacknation_medical
MONGODB_MAX_CONNECTIONS=10
MONGODB_MIN_CONNECTIONS=1

# =============================================================================
# VECTOR STORE (ChromaDB)
# =============================================================================
CHROMA_PERSIST_DIRECTORY=./data/vectorstore
CHROMA_COLLECTION_PREFIX=medical_kb

# =============================================================================
# PUBMED/NCBI CONFIGURATION
# =============================================================================
PUBMED_EMAIL=dc.lerma@ugto.mx
PUBMED_API_KEY=your_ncbi_api_key_optional
PUBMED_MAX_RESULTS=10
PUBMED_TOOL_NAME=ClinicalCrew

# =============================================================================
# API CONFIGURATION
# =============================================================================
API_V1_PREFIX=/api/v1
API_TITLE=Clinical Crew
API_VERSION=1.0.0
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================
MAX_INTERCONSULTAS_PARALELAS=5
TIMEOUT_ESPECIALISTA_SEGUNDOS=120
ENABLE_STREAMING=true

# =============================================================================
# LOGGING
# =============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Roadmap

### Fase 1: MVP (Actual)

- [x] Diseño de arquitectura
- [ ] Implementación de agentes básicos
- [ ] Sistema RAG funcional
- [ ] API REST completa
- [ ] 3 especialistas iniciales

### Fase 2: Mejoras

- [ ] Más especialistas (10+)
- [ ] Sistema de caché inteligente
- [ ] Métricas y observabilidad
- [ ] Tests automatizados completos
- [ ] CI/CD pipeline

### Fase 3: Producción

- [ ] Autenticación y autorización
- [ ] Rate limiting
- [ ] Multitenancy
- [ ] Backup y recuperación
- [ ] Compliance HIPAA/GDPR

### Fase 4: Características Avanzadas

- [ ] Integración con FHIR
- [ ] Análisis de imágenes médicas
- [ ] Generación de planes de tratamiento
- [ ] Sistema de alertas clínicas
- [ ] Dashboard de analytics

## Consideraciones Importantes

### Limitaciones y Disclaimers

1. **No es un dispositivo médico**: Este sistema es una herramienta de apoyo a la decisión clínica, NO un sustituto del juicio médico profesional.

2. **Validación requerida**: Toda recomendación debe ser validada por un profesional de la salud antes de aplicarse clínicamente.

3. **Evidencia actual**: El sistema se basa en evidencia disponible hasta la fecha de actualización de sus bases de conocimiento.

4. **Contexto limitado**: El sistema solo conoce la información que se le proporciona. Información faltante puede afectar las recomendaciones.

### Seguridad y Privacidad

1. **Datos sensibles**: Nunca incluir información identificable del paciente (PHI) en ambientes de desarrollo.

2. **Encriptación**: En producción, todos los datos deben estar encriptados en tránsito y reposo.

3. **Auditoría**: Todas las consultas y respuestas deben ser auditables.

4. **Compliance**: Asegurar cumplimiento con regulaciones locales (HIPAA en USA, GDPR en Europa, etc.).

## Soporte y Contribución

### Reportar Issues

GitHub Issues: [https://github.com/AI-Ethics-Community/clinical-crew/issues](https://github.com/AI-Ethics-Community/clinical-crew/issues)

### Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para guías de contribución.

### Contacto

**Autores del Proyecto:**

- Diego Lerma - [dc.lerma@ugto.mx](mailto:dc.lerma@ugto.mx)
- Karla Doctor - [ka.doctormauricio@gmail.com](mailto:ka.doctormauricio@gmail.com)

**Documentación:** [docs/](docs/)

## Licencia

[MIT License](LICENSE)

## Agradecimientos

**Clinical Crew** fue desarrollado por:

- **Diego Lerma** - Desarrollador Principal
- **Karla Doctor** - Co-Desarrolladora

Este proyecto es parte de la iniciativa AI Ethics Community.

### Tecnologías Utilizadas

- Google Gemini
- LangChain y LangGraph
- FastAPI
- MongoDB
- ChromaDB

---

**Versión:** 1.0.0
**Última actualización:** 2025-11-09
**Autores:** Diego Lerma, Karla Doctor
**Organización:** AI Ethics Community
