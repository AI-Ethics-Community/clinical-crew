# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Clinical Crew is a multi-agent medical consultation system developed by the AI Ethics Community that simulates the medical interconsultation process using specialized AI agents. The system uses LangGraph to orchestrate multiple specialist agents that work together to answer complex medical questions, with each agent having access to specialized knowledge bases via RAG and PubMed literature search.

**Repository:** https://github.com/AI-Ethics-Community/clinical-crew

**Key Workflow:** User submits a medical consultation → General Practitioner agent evaluates → If complex, generates interconsultation notes → Specialist agents process in parallel → GP integrates responses → Complete clinical record is generated.

## Development Commands

### Environment Setup

```bash
# Quick start (sets up venv, installs dependencies, starts MongoDB)
./quickstart.sh

# Manual setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add GEMINI_API_KEY and PUBMED_EMAIL
```

### Running the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Alternative
python -m app.main

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker & Database

```bash
# Start MongoDB only
docker-compose up -d mongodb

# Start all services (MongoDB + App)
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f
```

### RAG Knowledge Base

```bash
# Index all knowledge bases
python -m app.rag.document_indexer --all

# Index specific specialty
python -m app.rag.document_indexer --specialty cardiology
python -m app.rag.document_indexer --specialty endocrinology
python -m app.rag.document_indexer --specialty pharmacology
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_agents/test_graph.py

# Test PubMed keyword extraction
python test_pubmed_keywords.py

# Run example usage
python example_usage.py
```

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint
flake8 app/ tests/

# Type checking
mypy app/
```

## Architecture Overview

### Multi-Agent System (LangGraph)

The system uses a state machine workflow implemented with LangGraph:

1. **evaluate_initial_consultation**: GP evaluates if it can answer directly or needs specialists
2. **generate_interconsultations**: GP creates structured interconsultation notes for each required specialist
3. **execute_specialists**: All specialist agents run in parallel (using `asyncio.gather`)
4. **integrate_responses**: GP synthesizes all specialist responses into final answer

**Key Insight**: Specialists run in parallel for performance. The graph state (`MedicalConsultationState` in `app/agents/graph.py`) is passed through all nodes and contains the complete consultation context.

### Agent Architecture

- **General Practitioner Agent** (`app/agents/general_practitioner.py`): Coordinator agent that decides routing, generates interconsultations, and integrates responses. Uses Gemini Pro.
- **Specialist Agents** (`app/agents/specialists/`): Base class pattern with specialty-specific instances. Each has RAG access to specialty knowledge base + PubMed search. Uses Gemini Flash for speed.
- **Configuration**: Specialists are configured in `app/config/specialists.yaml` (or `especialistas.yaml`)

### RAG System

- **Embeddings**: Google Gemini embeddings (`models/text-embedding-004`)
- **Vector Store**: ChromaDB with persistent storage in `./data/vectorstore`
- **Document Organization**: Knowledge base documents organized by specialty in `data/knowledge_base/{specialty}/`
- **Retrieval**: Semantic search with hybrid vector + keyword matching (`app/rag/retriever.py`)

### Database Schema (MongoDB with Beanie ODM)

Primary collection: `MedicalConsultation` (defined in `app/models/database.py`)

Key fields:

- `estado`: "evaluando" | "interconsultando" | "esperando_info" | "completado"
- `general_evaluation`: GP's initial assessment
- `interconsultations[]`: Array of interconsultation notes
- `counter_referrals[]`: Array of specialist responses
- `clinical_record`: Final integrated clinical record
- `execution_trace[]`: Debugging/monitoring trace of workflow steps

### API Structure

FastAPI endpoints in `app/api/v1/`:

- `POST /api/v1/consultation` - Create new consultation (synchronous, returns when complete)
- `GET /api/v1/consultation/{id}` - Get complete consultation
- `GET /api/v1/consultation/{id}/status` - Get consultation status
- `POST /api/v1/consultation/{id}/responder` - Provide additional information

## Important Implementation Details

### Bilingual Support and PubMed Integration

**Key Feature**: The system accepts Spanish medical consultations and intelligently translates them to English MeSH terms for PubMed searches.

**Keyword Extraction Pipeline** (`app/services/pubmed_client.py` and `app/agents/prompts/pubmed_keywords.py`):

1. Spanish consultation question received
2. Gemini Flash extracts 3-5 core medical concepts
3. Concepts translated to standard English medical terminology
4. MeSH (Medical Subject Headings) terms suggested when applicable
5. Optimized PubMed search query generated

Example flow:
```python
# Input (Spanish)
"Paciente con diabetes gestacional de 28 semanas con mal control glucémico"

# Output (English MeSH)
{
  "keywords": ["gestational diabetes", "pregnancy", "third trimester", "glycemic control"],
  "mesh_terms": ["diabetes, gestational[mesh]", "pregnancy trimester, third[mesh]"],
  "suggested_query": "diabetes, gestational[mesh] AND pregnancy trimester, third[mesh] AND blood glucose[mesh]"
}
```

This ensures high-quality, evidence-based literature retrieval from PubMed regardless of input language.

### Medical Note Generation

The system uses structured medical note formats (`app/services/notas_service.py`):

- **Interconsultation Note**: Sent from GP to specialist (context + specific question)
- **Counter-referral Note**: Specialist's response (evaluation + evidence + recommendations)
- **Clinical Record**: Final formatted document with complete consultation history

### Parallel Execution

Specialists execute in parallel using:

```python
tasks = [process_interconsulta(ic) for ic in state['interconsultations']]
counter_referrals = await asyncio.gather(*tasks)
```

This is critical for performance when multiple specialists are needed.

### Configuration System

Uses Pydantic Settings with `.env` file. All settings in `app/config/settings.py`. Access via:

```python
from app.config.settings import settings
settings.gemini_api_key
```

### Adding New Specialists

1. Add configuration to `app/config/specialists.yaml`
2. Add knowledge base documents to `data/knowledge_base/{specialty}/`
3. Run `python -m app.rag.document_indexer --specialty {specialty}`
4. (Optional) Create custom specialist class in `app/agents/specialists/{specialty}.py` if special logic needed
5. System automatically detects and loads specialists from config

## Code Style & Patterns

### Python/FastAPI Conventions

**Type Hints & Validation:**

- Use type hints for all function signatures
- Use Pydantic models for input validation and response schemas (never raw dictionaries)
- Example:
  ```python
  async def create_consultation(
      consultation: ConsultationCreate,
      db: AsyncIOMotorDatabase = Depends(get_database)
  ) -> ConsultationResponse:
      ...
  ```

**Async/Await Patterns:**

- Use `async def` for all I/O-bound operations (database, external APIs, LLM calls)
- Use `def` only for pure synchronous functions
- Minimize blocking operations in routes and agent nodes
- Example pattern:

  ```python
  # Good: Non-blocking parallel execution
  tasks = [specialist.process(ic) for ic in interconsultations]
  results = await asyncio.gather(*tasks)

  # Bad: Sequential blocking
  results = [await specialist.process(ic) for ic in interconsultations]
  ```

**Error Handling:**

- Handle errors early with guard clauses
- Use early returns to avoid deeply nested conditionals
- Use `HTTPException` for expected API errors
- Log unexpected errors with context
- Example:

  ```python
  async def get_consultation(consultation_id: str) -> MedicalConsultation:
      # Guard clause - handle error early
      if not ObjectId.is_valid(consultation_id):
          raise HTTPException(status_code=400, detail="Invalid consultation ID")

      consultation = await MedicalConsultation.get(consultation_id)
      if not consultation:
          raise HTTPException(status_code=404, detail="Consultation not found")

      # Happy path last
      return consultation
  ```

**File Organization:**

- Use lowercase with underscores for files and directories: `user_routes.py`, `gemini_client.py`
- File structure: router/endpoints → business logic → utilities → models
- Keep route handlers thin - delegate complex logic to service functions

**Naming Conventions:**

- Use descriptive variable names with auxiliary verbs: `is_completed`, `has_specialists`, `can_answer_directly`
- Function names should be verb phrases: `evaluate_consultation`, `generate_interconsultations`
- Avoid abbreviations unless widely understood in medical context

### FastAPI-Specific Patterns

**Dependency Injection:**

- Use FastAPI's dependency injection for shared resources (database, settings, clients)
- Example:

  ```python
  from app.api.dependencies import get_database, get_gemini_client

  @router.post("/consultation")
  async def create_consultation(
      request: ConsultationRequest,
      db: AsyncIOMotorDatabase = Depends(get_database),
      gemini: GeminiClient = Depends(get_gemini_client)
  ):
      ...
  ```

**Lifespan Management:**

- Use lifespan context managers (not `@app.on_event`) for startup/shutdown
- See `app/main.py` for reference implementation

**Response Models:**

- Always specify response_model in route decorators
- Use Pydantic models for consistent serialization
- Example:
  ```python
  @router.get("/consultation/{id}", response_model=ConsultationResponse)
  async def get_consultation(id: str):
      ...
  ```

### LangGraph-Specific Patterns

**State Management:**

- Always type the state with TypedDict
- Pass complete context through state, don't rely on global variables
- Update state immutably in node functions
- Example:
  ```python
  async def node_function(state: MedicalConsultationState) -> MedicalConsultationState:
      # Create new state dict with updates
      return {
          **state,
          'new_field': value,
          'estado': 'new_status'
      }
  ```

**Node Functions:**

- Keep nodes focused on single responsibility
- Handle errors within nodes and update state accordingly
- Always return the state type
- Use async for all node functions that do I/O

**Conditional Edges:**

- Router functions should be pure (no side effects)
- Return string literals that match edge names
- Keep routing logic simple and testable

### Performance Best Practices

**Async I/O:**

- Never use blocking I/O in async functions
- Use async libraries: `motor` (MongoDB), `httpx` (HTTP), `aiofiles` (files)
- For CPU-bound tasks, consider `asyncio.to_thread()` or process pools

**Database Queries:**

- Use indexes on frequently queried fields
- Project only needed fields in queries
- Avoid N+1 queries - fetch related data in single queries when possible

**LLM Calls:**

- Use parallel execution for independent LLM calls (specialists)
- Set appropriate timeouts
- Implement retry logic with exponential backoff
- Cache results when appropriate

**Caching Strategy:**

- Cache expensive computations (embeddings, RAG retrievals)
- Consider Redis for distributed caching if scaling
- Use TTL for medical data to ensure freshness

### Testing Patterns

**Async Testing:**

- Use `pytest-asyncio` for testing async functions
- Mark tests with `@pytest.mark.asyncio`
- Mock external services (Gemini API, PubMed)

**Test Structure:**

- Arrange-Act-Assert pattern
- Use fixtures for common setup (test database, mock clients)
- Test error cases and edge cases, not just happy paths

## Translation and Bilingual Support

### Codebase Translation Status

The codebase is in transition from Spanish to English. There's a `translate_project.py` script for automated translation.

When editing files, prefer the English naming convention:

- `especialistas` → `specialists`
- `consultas.py` → `consultations.py`
- `notas.py` → `notes.py`
- Variable names should use English: `pregunta` → `question`, `respuesta` → `response`

**Current state**: Many internal variables and some docstrings remain in Spanish. This is acceptable during transition, but new code should use English.

### User-Facing Bilingual Support

**Important distinction**: While the codebase is being translated to English, the **application itself is bilingual**:

- **Input**: Accepts medical consultations in Spanish (primary use case for Latin American medical professionals)
- **Processing**: Internal processing and PubMed searches use English medical terminology
- **Output**: Clinical records and responses are in Spanish for end users

**Translation Pipeline**:
- Spanish medical query → Gemini extracts concepts → English MeSH terms → PubMed search → Spanish clinical response

This dual-language architecture is intentional and should be preserved.

## Environment Variables

Required:

- `GEMINI_API_KEY` - Google Gemini API key
- `PUBMED_EMAIL` - Email for PubMed API (required by NCBI)

Optional but recommended:

- `PUBMED_API_KEY` - NCBI API key for higher rate limits
- `MONGODB_URL` - MongoDB connection string (default: `mongodb://localhost:27017`)
- `CHROMA_PERSIST_DIRECTORY` - ChromaDB storage path (default: `./data/vectorstore`)

See `.env.example` for complete list.

## Key Dependencies

- **langchain/langgraph**: Agent orchestration and workflow
- **google-generativeai**: Gemini LLM integration
- **fastapi**: Web framework
- **beanie/motor**: MongoDB async ORM
- **chromadb**: Vector database for RAG
- **biopython**: PubMed/NCBI API access

## Project Structure Highlights

```text
app/
├── agents/           # Multi-agent system (LangGraph)
│   ├── graph.py     # Main workflow definition
│   ├── general_practitioner.py
│   ├── specialists/ # Specialist agents
│   └── prompts/     # System prompts
│       ├── general_practitioner.py  # GP agent prompts
│       ├── specialists.py           # Specialist agent prompts
│       └── pubmed_keywords.py       # PubMed keyword extraction prompts
├── api/v1/          # FastAPI endpoints
├── models/          # Pydantic models + Beanie ODM
├── rag/             # RAG system (embeddings, vector store, retrieval)
├── services/        # External services (Gemini, PubMed, notes generation)
└── config/          # Settings and specialist configuration

data/
├── knowledge_base/  # Documents by specialty (PDF, DOCX, MD)
└── vectorstore/     # ChromaDB persistent storage
```

## Medical Domain Context

This system mimics real medical interconsultation workflow:

- **Interconsultation**: When a doctor consults a specialist for expertise
- **Counter-referral**: Specialist's response back to the requesting doctor
- **Clinical Record**: Complete documentation of patient care

The system prioritizes evidence-based medicine with citations from medical literature (PubMed) and clinical guidelines.

## Common Errors and Solutions

### Import Errors (Spanish/English Naming Mismatch)

The codebase is transitioning from Spanish to English. Common import errors:

**Problem:** `cannot import name 'ConsultationCreate'`
**Solution:** The actual class is `ConsultaCreate`. Use aliases in `app/models/__init__.py`:

```python
from app.models.consultation import ConsultaCreate as ConsultationCreate
```

**Problem:** `ModuleNotFoundError: No module named 'app.rag.indexer'`
**Solution:** The file is named `document_indexer.py`, not `indexer.py`:

```python
from app.rag.document_indexer import DocumentIndexer, indexer
```

**Problem:** `ModuleNotFoundError: No module named 'app.services.notas_service'`
**Solution:** The file is `notes_service.py`:

```python
from app.services.notes_service import notas_service
```

**Problem:** `Specialty not found in config: cardiologia`
**Solution:** Config uses English names. Update specialist agent constructors:

```python
# app/agents/specialists/cardiology.py
super().__init__(specialty="cardiology")  # not "cardiologia"
```

### Dependency Conflicts

**Problem:** `numpy==2.1.3` conflicts with `langchain`
**Solution:** Use compatible version in `requirements.txt`:

```python
numpy<2.0.0,>=1.26.0  # langchain requires numpy < 2.0
```

**Problem:** `pymongo==4.10.1` conflicts with `motor`
**Solution:**

```python
pymongo<4.10,>=4.9  # motor 3.6.0 requires pymongo < 4.10
```

### Pydantic Settings Errors

**Problem:** `"Config" and "model_config" cannot be used together`
**Solution:** Remove the inner `Config` class from `Settings` in `app/config/settings.py`. Use only `model_config` (Pydantic v2 style).

**Problem:** `error parsing value for field "cors_origins"`
**Solution:** Use a property to parse comma-separated CORS origins:

```python
cors_origins_str: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

@property
def cors_origins(self) -> List[str]:
    return [origin.strip() for origin in self.cors_origins_str.split(",")]
```

### Database Initialization Errors

**Problem:** `AttributeError: init_beanie`
**Solution:** Import `init_beanie` directly from `beanie`:

```python
from beanie import init_beanie

async def init_db(database):
    await init_beanie(database=database, document_models=[...])
```

### Specialist Agent Configuration

The specialist mapping in `app/agents/specialists/__init__.py` must match the config file:

**Config file** (`app/config/specialists.yaml`):

```yaml
specialists:
  cardiology: # English
  endocrinology: # English
  pharmacology: # English
```

**Agent dictionary** must use same keys:

```python
SPECIALIST_AGENTS = {
    "cardiology": cardiology_agent,  # Match config
    "endocrinology": endocrinology_agent,
    "pharmacology": pharmacology_agent,
}
```

## Debugging Tips

### General Debugging

- Check `execution_trace` field in MongoDB documents to see workflow progression
- MongoDB health check: `docker exec hacknation_mongodb mongosh --eval "db.adminCommand('ping')"`
- ChromaDB collections: Check `./data/vectorstore` directory
- API interactive docs: `http://localhost:8000/docs`
- Use `example_usage.py` for quick API testing
- Check running server: `ps aux | grep "python3 -m app.main"`
- View real-time logs when running in background: Check the BashOutput for the running process

### PubMed Keyword Extraction Debugging

When debugging PubMed searches:

```python
# The PubMedClient now includes keyword extraction
# Check what keywords are being extracted:
client = PubMedClient()
result = await client.extract_medical_keywords_async(
    pregunta="Paciente con diabetes...",
    specialty="endocrinology"
)
print(f"Keywords: {result['keywords']}")
print(f"MeSH terms: {result['mesh_terms']}")
print(f"Query: {result['suggested_query']}")
```

Common issues:
- If PubMed returns too few results, check if MeSH terms are too specific
- If getting irrelevant results, verify keyword extraction is working correctly
- Gemini Flash model must be configured with low temperature (0.1) for consistent keyword extraction

### Quick Verification Commands

```bash
# Health check
curl http://localhost:8000/health

# MongoDB connection
mongosh --eval "db.adminCommand('ping')"

# Check if port 8000 is in use
lsof -i :8000

# View all environment variables
python3 -c "from app.config.settings import settings; import json; print(json.dumps({k:v for k,v in settings.__dict__.items() if not k.startswith('_')}, indent=2, default=str))"
```
