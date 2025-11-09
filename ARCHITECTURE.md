# 🏥 Clinical Crew - Complete Architecture Guide

## 📊 High-Level Architecture (10,000 Foot View)

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│                  (Doctor with a question)                        │
└────────────────────┬────────────────────────────────────────────┘
                     │ POST /api/v1/consultation
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI (app/main.py)                      │
│  • Receives medical consultation in Spanish                     │
│  • Validates data with Pydantic                                 │
│  • Initiates LangGraph workflow                                 │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│              LangGraph Workflow (app/agents/graph.py)           │
│                                                                  │
│  [Evaluate] → [Interconsult] → [Specialists] → [Integrate]     │
│       GP             GP              Parallel           GP      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MongoDB (Beanie ODM)                         │
│  • Stores complete consultation history                         │
│  • Execution trace for debugging                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Step-by-Step Flow

### **Step 1: Consultation Reception**

**Location**: `app/api/v1/consultas.py`

```python
# User sends:
{
  "consultation": "Patient with decompensated type 2 diabetes. Can I start sertraline?",
  "contexto": {
    "edad": 45,
    "sexo": "male",
    "diagnosticos": ["Type 2 Diabetes"],
    "medicamentos_actuales": ["Metformin 850mg"]
  }
}
```

**What happens:**
1. FastAPI validates data with Pydantic (`ConsultaCreate`)
2. Creates a document in MongoDB (`MedicalConsultation`)
3. Initiates LangGraph workflow

---

### **Step 2: Node 1 - Initial Evaluation**

**Location**: `app/agents/graph.py` → function `evaluate_initial_consultation()`

**Responsible**: **General Practitioner (GP)** - `app/agents/general_practitioner.py`

```python
async def evaluate_initial_consultation(state):
    # GP analyzes the question
    evaluacion = await general_practitioner.evaluate_consultation(
        consultation=state['original_consultation'],
        patient_context=contexto
    )
    # Decides: Can I answer or do I need specialists?
    return state
```

**What does the GP do here?**

1. **Reads the prompt**: `app/agents/prompts/general_practitioner.py` → `PROMPT_EVALUACION_INICIAL`
2. **Calls Gemini Pro**: Using `app/services/gemini_client.py`
3. **Gemini decides**:
   - `can_answer_directly: false` → "I need help, this is complex"
   - `required_specialists: ["endocrinology", "pharmacology"]` → "I need these specialists"
   - `razonamiento: "Complex case, drug interactions..."` → "Here's why"

4. **Updates MongoDB**: Saves the evaluation

**Result from Step 2:**
```python
{
  "can_answer_directly": false,
  "required_specialists": ["endocrinology", "pharmacology"],
  "razonamiento": "Decompensated diabetes + antidepressant requires endocrine and pharmacological evaluation",
  "estimated_complexity": 0.7
}
```

---

### **Step 3: Node 2 - Generate Interconsultations**

**Location**: `app/agents/graph.py` → function `generate_interconsultations()`

**Responsible**: General Practitioner (GP)

```python
async def generate_interconsultations(state):
    # For each required specialist
    for specialty in ["endocrinology", "pharmacology"]:
        # GP generates a personalized interconsultation note
        interconsultation = await general_practitioner.generate_interconsulta(
            specialty=specialty,
            consultation=state['original_consultation'],
            patient_context=contexto
        )
        interconsultations.append(interconsultation)

    return state
```

**What does it do?**

The GP creates **structured interconsultation notes** for each specialist:

```python
# Interconsultation for Endocrinology:
{
  "specialty": "endocrinology",
  "specific_question": "Is it safe to start sertraline in patient with decompensated T2DM?",
  "relevant_context": {
    "primary_diagnosis": "Decompensated Type 2 Diabetes",
    "current_treatment": "Metformin 850mg",
    "additional_context": "Requires antidepressant"
  }
}

# Interconsultation for Pharmacology:
{
  "specialty": "pharmacology",
  "specific_question": "Are there interactions between sertraline and metformin?",
  "relevant_context": {
    "proposed_medication": "Sertraline",
    "current_medications": ["Metformin 850mg"]
  }
}
```

**Format**: `app/services/notes_service.py` → `generar_nota_interconsulta()`

---

### **Step 4: Node 3 - Execute Specialists (PARALLEL)**

**Location**: `app/agents/graph.py` → function `execute_specialists()`

**KEY**: Specialists execute **in parallel** using `asyncio.gather()`

```python
async def execute_specialists(state):
    # Define function to process each interconsultation
    async def process_interconsulta(interconsulta_data):
        # 1. Get specialist agent
        specialist = get_specialist_agent(interconsulta_data['specialty'])

        # 2. Process interconsultation
        counter_referral = await specialist.process_interconsulta(...)

        return counter_referral

    # 3. EXECUTE ALL IN PARALLEL
    tasks = [process_interconsulta(ic) for ic in state['interconsultations']]
    counter_referrals = await asyncio.gather(*tasks)

    return state
```

#### **What does each Specialist do?**

**Location**: `app/agents/specialists/base.py` → class `SpecialistAgent`

**Each specialist (endocrinology, pharmacology, cardiology) follows the same process:**

```python
async def process_interconsulta(self, pregunta, contexto, patient_context):
    # STEP A: Search in RAG (Local knowledge)
    rag_context = await self._retrieve_from_rag(pregunta)

    # STEP B: Search PubMed (Scientific literature)
    pubmed_context = await self._search_pubmed(pregunta)

    # STEP C: Generate response with Gemini
    response = await self._generate_response(
        pregunta=pregunta,
        rag_context=rag_context,
        pubmed_context=pubmed_context
    )

    # STEP D: Create structured counter-referral
    return counter_referral
```

##### **STEP A: RAG (Retrieval Augmented Generation)**

**Location**: `app/rag/retriever.py`

```python
# 1. Convert question to embeddings (vectors)
embedding = await embeddings.get_embedding(pregunta)

# 2. Search ChromaDB for similar documents
# Physical location: data/vectorstore/
results = vector_store.search(
    collection="endocrinology_kb",  # Endocrinology knowledge base
    query_embedding=embedding,
    top_k=5
)

# 3. Returns fragments from clinical guidelines, books, etc.
# Example:
"""
ADA Guidelines 2024: In patients with T2DM requiring antidepressants,
SSRIs are safe but require glycemic monitoring...
"""
```

**Where do these documents come from?**
- `data/knowledge_base/endocrinology/` → PDFs, DOCX, MD
- Indexed with: `python -m app.rag.document_indexer --specialty endocrinology`
- Stored in: `data/vectorstore/` (ChromaDB)

##### **STEP B: PubMed Search**

**Location**: `app/services/pubmed_client.py`

**NEW FEATURE**: Intelligent translation from Spanish to MeSH terms

```python
# 1. Extract keywords from Spanish question
# Location: app/agents/prompts/pubmed_keywords.py
keywords = await extract_medical_keywords_async(
    pregunta="Patient with type 2 diabetes needs sertraline",
    specialty="endocrinology"
)
# Result:
{
  "keywords": ["type 2 diabetes", "SSRI", "sertraline", "glycemic control"],
  "mesh_terms": ["diabetes mellitus, type 2[mesh]", "sertraline[mesh]"],
  "suggested_query": "diabetes mellitus, type 2[mesh] AND sertraline[mesh]"
}

# 2. Search PubMed with English terms
articles = await search_pubmed(query=keywords['suggested_query'])

# 3. Get article abstracts
# Example:
"""
PMID: 12345678
Title: Safety of SSRIs in Type 2 Diabetes
Abstract: Sertraline shows minimal effect on glycemic control...
"""
```

**Libraries used:**
- `Biopython` → To access PubMed/NCBI
- `google.generativeai` → To extract keywords with Gemini Flash

##### **STEP C: Generate Response with Gemini**

**Location**: `app/agents/specialists/base.py` → `_generate_response()`

```python
# The specialist receives:
# 1. Specific question
# 2. Patient context
# 3. RAG information (local clinical guidelines)
# 4. PubMed information (scientific literature)
# 5. Specialist prompt (from specialists.yaml)

# Gemini generates a structured response:
{
  "evaluacion": "Patient with T2DM requires interaction evaluation...",
  "evidence_used": [
    "ADA Guidelines 2024",
    "PMID: 12345678 - SSRIs in Diabetes"
  ],
  "clinical_reasoning": "SSRIs may affect glycemic control...",
  "respuesta": "RECOMMENDATIONS:\n1. Start sertraline 25-50mg\n2. Monitor...",
  "requires_additional_info": false,
  "additional_questions": []
}
```

##### **STEP D: Create Counter-Referral**

**Format**: `app/models/consultation.py` → class `CounterReferralNote`

The response is structured as a **formal medical note**:

```
COUNTER-REFERRAL NOTE - ENDOCRINOLOGY

EVALUATION:
Patient with decompensated T2DM requires SSRI antidepressant initiation.

EVIDENCE REVIEWED:
- ADA Standards of Care in Diabetes 2024
- PMID: 12345678 - Safety of SSRIs in T2DM

CLINICAL REASONING:
SSRIs like sertraline have dual effect on glycemia...

RESPONSE:
RECOMMENDATIONS:
1. Yes, can start sertraline 25-50mg
2. Capillary glucose monitoring 3 times/day x 2 weeks
3. Follow-up in 1 week

EVIDENCE LEVEL: High
```

---

### **Step 5: Node 4 - Integrate Responses**

**Location**: `app/agents/graph.py` → function `integrate_responses()`

**Responsible**: General Practitioner (GP)

```python
async def integrate_responses(state):
    # GP receives all counter-referrals
    response_data = await general_practitioner.integrate_responses(
        consultation=state['original_consultation'],
        patient_context=contexto,
        counter_referrals=counter_referrals  # From all specialists
    )

    # Generate complete clinical record
    expediente_text = notas_service.generar_expediente_completo(...)

    return state
```

**What does the GP do?**

1. **Reads all counter-referrals** (endocrinology + pharmacology)
2. **Synthesizes**: Identifies consensus, discrepancies, priorities
3. **Generates integrated plan**:

```
INTERCONSULTATION INTEGRATION

CONSULTATION: Patient with T2DM, can I start sertraline?

ANSWER: YES, WITH PRECAUTIONS

RATIONALE:

1. ENDOCRINE SAFETY (Endocrinology):
   - Sertraline is safe in T2DM
   - Requires close glycemic monitoring
   - May have biphasic effect on glycemia

2. PHARMACOLOGICAL SAFETY (Pharmacology):
   - Sertraline-Metformin interaction: Minimal
   - No dose adjustment required
   - No contraindications

INTEGRATED THERAPEUTIC PLAN:
1. START: Sertraline 25-50mg in morning
2. MONITORING: Capillary glucose 3 times/day x 2 weeks
3. FOLLOW-UP: Appointment in 1 week
4. EDUCATION: Hypoglycemia warning signs

EVIDENCE LEVEL: High (ADA 2024 Guidelines, clinical studies)
```

---

## 📂 Where is Everything Located?

### **1. Entry Point (API)**

```
app/
├── main.py                    # FastAPI app, startup, lifespan
├── api/
│   ├── v1/
│   │   ├── consultas.py      # POST /api/v1/consultation
│   │   └── websockets.py     # WebSocket streaming
│   └── dependencies.py        # get_database(), get_gemini_client()
```

**`main.py`**: Starts server, connects to MongoDB, configures CORS

### **2. Agents (LangGraph)**

```
app/agents/
├── graph.py                   # COMPLETE WORKFLOW (StateGraph)
│                              # - evaluate_initial_consultation()
│                              # - generate_interconsultations()
│                              # - execute_specialists()
│                              # - integrate_responses()
│
├── general_practitioner.py    # General Practitioner
│                              # - evaluate_consultation()
│                              # - generate_interconsulta()
│                              # - integrate_responses()
│
├── specialists/
│   ├── base.py               # SpecialistAgent class
│   │                         # - process_interconsulta()
│   │                         # - _retrieve_from_rag()
│   │                         # - _search_pubmed()
│   │                         # - _generate_response()
│   │
│   ├── cardiology.py         # Cardiology Specialist (inherits from base)
│   ├── endocrinology.py      # Endocrinology Specialist
│   ├── pharmacology.py       # Pharmacology Specialist
│   └── __init__.py           # get_specialist_agent()
│
└── prompts/
    ├── general_practitioner.py   # GP prompts
    ├── specialists.py            # Specialist prompts
    └── pubmed_keywords.py        # Keyword extraction prompt
```

**`graph.py`**: The heart of the system. Defines the complete workflow.

### **3. Data Models**

```
app/models/
├── consultation.py           # Pydantic models
│                            # - ConsultaCreate (API input)
│                            # - PatientContext
│                            # - EvaluacionGeneral
│                            # - InterconsultationNote
│                            # - CounterReferralNote
│                            # - ClinicalRecord
│
├── database.py              # MongoDB/Beanie models
│                            # - MedicalConsultation (main document)
│                            # - BusquedaPubMed
│
└── notes.py                 # Medical note formatting
                             # - FormatoContextoPaciente
                             # - FormatoNotaInterconsulta
```

### **4. RAG (Local Knowledge)**

```
app/rag/
├── embeddings.py             # Google Gemini Embeddings
│                            # - get_embedding()
│                            # - batch_get_embeddings()
│
├── vector_store.py          # ChromaDB wrapper
│                            # - add_documents()
│                            # - search()
│
├── document_indexer.py      # Index documents
│                            # - index_specialty()
│                            # - Command: python -m app.rag.document_indexer --all
│
└── retriever.py             # Semantic search
                             # - retrieve()
```

**Physical data**:
```
data/
├── knowledge_base/          # Source documents
│   ├── cardiology/          # PDFs, DOCX, MD for cardiology
│   ├── endocrinology/
│   └── pharmacology/
│
└── vectorstore/             # ChromaDB (auto-generated)
    ├── chroma.sqlite3
    └── embeddings/
```

### **5. External Services**

```
app/services/
├── gemini_client.py         # Google Gemini LLM
│                           # - gemini_medico_general (Gemini Pro)
│                           # - gemini_especialista (Gemini Flash)
│                           # - generate_content_async()
│
├── pubmed_client.py        # PubMed/NCBI
│                           # - extract_medical_keywords_async() ← NEW
│                           # - search_pubmed()
│                           # - get_article_details()
│
└── notes_service.py        # Medical note generation
                            # - generar_nota_interconsulta()
                            # - generar_nota_contrarreferencia()
                            # - generar_expediente_completo()
```

### **6. Configuration**

```
app/config/
├── settings.py              # Pydantic Settings
│                           # - GEMINI_API_KEY
│                           # - PUBMED_EMAIL
│                           # - MONGODB_URL
│
└── specialists.yaml         # Specialist configuration
                            # - Name, description
                            # - Custom prompts
                            # - Areas of expertise
```

### **7. Database (MongoDB)**

```
MongoDB Collection: medical_consultations

Example document:
{
  "_id": ObjectId("..."),
  "original_consultation": "Patient with diabetes...",
  "patient_context": { edad: 45, ... },
  "estado": "completed",  // evaluating | consulting | completed

  "general_evaluation": {
    "can_answer_directly": false,
    "required_specialists": ["endocrinology", "pharmacology"]
  },

  "interconsultations": [
    { specialty: "endocrinology", specific_question: "...", ... },
    { specialty: "pharmacology", specific_question: "...", ... }
  ],

  "counter_referrals": [
    { specialty: "endocrinology", respuesta: "...", evidence_used: [...] },
    { specialty: "pharmacology", respuesta: "...", evidence_used: [...] }
  ],

  "clinical_record": {
    "general_summary": "...",
    "complete_notes": "COMPLETE CLINICAL RECORD...",
    "final_response": "THERAPEUTIC PLAN..."
  },

  "execution_trace": [
    { step: "evaluate_consultation", timestamp: "...", data: {...} },
    { step: "execute_specialists", timestamp: "...", data: {...} }
  ]
}
```

---

## 🔑 Key Concepts

### **1. LangGraph State Machine**

```python
# State flows through all nodes
MedicalConsultationState = {
    "original_consultation": str,
    "patient_context": dict,
    "general_evaluation": dict,      # From GP
    "interconsultations": list,      # From GP
    "counter_referrals": list,       # From specialists
    "clinical_record": dict,         # Final
    "estado": str                    # Flow control
}
```

Each node receives the state, modifies it, and returns it:

```python
async def node_function(state: MedicalConsultationState) -> MedicalConsultationState:
    # Process
    state['new_field'] = result
    state['estado'] = 'new_state'
    return state
```

### **2. Parallel Execution**

```python
# ❌ BAD: Sequential (slow)
for specialist in specialists:
    result = await specialist.process()

# ✅ GOOD: Parallel (fast)
tasks = [specialist.process() for specialist in specialists]
results = await asyncio.gather(*tasks)
```

If 3 specialists take 30 seconds each:
- Sequential: 90 seconds
- Parallel: 30 seconds

### **3. RAG (Retrieval Augmented Generation)**

**Without RAG**:
```
Question → LLM → Response (only model knowledge)
```

**With RAG**:
```
Question → Search docs → Contextualize → LLM → Better informed response
```

Example:
```python
# 1. Convert question to vector
embedding = [0.234, -0.567, 0.123, ...]  # 768 dimensions

# 2. Search for similar documents in ChromaDB
results = vector_store.search(embedding)

# 3. Use context in prompt
prompt = f"""
Based on these clinical guidelines:
{rag_context}

Answer: {question}
"""
```

### **4. Bilingual Architecture**

```
User (Spanish) → API (Spanish) → Internal processing (English for PubMed) → Response (Spanish)
```

**Why?**
- PubMed only works well in English
- Medical users in Latin America speak Spanish
- System intelligently translates with Gemini

---

## 🎯 Visual Data Flow

```
User
  ↓
┌─────────────────────────┐
│ POST /api/v1/consultation│
└───────────┬─────────────┘
            ↓
    ┌───────────────┐
    │   MongoDB     │ ← Save initial consultation
    └───────────────┘
            ↓
    ┌────────────────────────────┐
    │  LangGraph Workflow        │
    │  ┌──────────────────────┐  │
    │  │ 1. evaluate_initial  │  │ → GP evaluates
    │  └──────────┬───────────┘  │
    │             ↓               │
    │  ┌──────────────────────┐  │
    │  │ 2. generate_interconsultations │ → GP creates notes
    │  └──────────┬───────────┘  │
    │             ↓               │
    │  ┌──────────────────────┐  │
    │  │ 3. execute_specialists│  │ → Parallel
    │  │   ┌─────┐ ┌─────┐    │  │
    │  │   │Endo │ │Pharm│ ...│  │
    │  │   │     │ │     │    │  │
    │  │   │ RAG │ │ RAG │    │  │
    │  │   │  +  │ │  +  │    │  │
    │  │   │PubMed│PubMed│    │  │
    │  │   │  +  │ │  +  │    │  │
    │  │   │Gemini│Gemini│    │  │
    │  │   └─────┘ └─────┘    │  │
    │  └──────────┬───────────┘  │
    │             ↓               │
    │  ┌──────────────────────┐  │
    │  │ 4. integrate_responses│  │ → GP integrates
    │  └──────────┬───────────┘  │
    └─────────────┼──────────────┘
                  ↓
          ┌───────────────┐
          │   MongoDB     │ ← Save complete result
          └───────────────┘
                  ↓
          Complete Clinical Record
```

---

## 🛠️ Technical Implementation Details

### **LangGraph Workflow Definition**

**Location**: `app/agents/graph.py`

```python
# Create state graph
workflow = StateGraph(MedicalConsultationState)

# Add nodes
workflow.add_node("evaluate_initial", evaluate_initial_consultation)
workflow.add_node("generate_interconsultations", generate_interconsultations)
workflow.add_node("execute_specialists", execute_specialists)
workflow.add_node("integrate_responses", integrate_responses)

# Add edges (flow control)
workflow.set_entry_point("evaluate_initial")

# Conditional routing
workflow.add_conditional_edges(
    "evaluate_initial",
    should_continue_to_specialists,
    {
        "direct_response": END,
        "need_specialists": "generate_interconsultations"
    }
)

workflow.add_edge("generate_interconsultations", "execute_specialists")
workflow.add_edge("execute_specialists", "integrate_responses")
workflow.add_edge("integrate_responses", END)

# Compile
app = workflow.compile()
```

### **Specialist Configuration (specialists.yaml)**

Each specialist has:

1. **Identity**: Name, description
2. **LLM Config**: Model (Gemini Pro), temperature (0.05)
3. **Tools**: RAG search, PubMed search, diagnostic criteria
4. **System Prompt**: Detailed instructions on how to respond
5. **Expert Topics**: Areas of specialization

Example for Cardiology:

```yaml
specialists:
  cardiology:
    name: "Cardiology"
    description: "Specialist in heart diseases and cardiovascular system"
    model: "models/gemini-2.5-pro"
    temperature: 0.05
    rag_collection: "cardiology_kb"
    enabled: true

    tools:
      - pubmed_search
      - rag_search
      - diagnostic_criteria

    system_prompt: |
      You are an expert cardiologist with extensive clinical experience.

      Your approach should be based on:
      1. ACC/AHA, ESC clinical practice guidelines
      2. Current scientific evidence
      3. Established diagnostic criteria
      4. Evidence-based medicine

      CRITICAL RULES - DO NOT FABRICATE DATA:
      ⚠️ Work ONLY with data explicitly provided in patient context
      ⚠️ If critical information is MISSING, set "requires_additional_info": true
      ⚠️ It is BETTER to request missing information than to fabricate data

    expert_topics:
      - Heart failure
      - Ischemic heart disease
      - Arrhythmias
      - Valvular heart disease
```

### **RAG Document Indexing Process**

**Command**: `python -m app.rag.document_indexer --specialty cardiology`

**What happens**:

1. **Read documents**: `data/knowledge_base/cardiology/*.pdf`
2. **Extract text**: PyPDF2, python-docx, markdown
3. **Chunk text**: Split into 1000-character chunks with 200-char overlap
4. **Generate embeddings**: Google Gemini Embeddings API
5. **Store in ChromaDB**: Vector database with metadata
6. **Create collection**: `cardiology_kb`

**Retrieval**:
```python
# When specialist receives question
query_embedding = await embeddings.get_embedding("heart failure treatment")
results = vector_store.search(
    collection="cardiology_kb",
    query_embedding=query_embedding,
    top_k=5
)
# Returns: 5 most relevant document chunks
```

### **PubMed Keyword Extraction**

**New Feature** - `app/agents/prompts/pubmed_keywords.py`

**Problem**: Spanish medical questions don't work well in PubMed (English-based)

**Solution**: Use Gemini Flash to intelligently extract and translate keywords

**Process**:

1. **Input**: Spanish medical question
   - "Paciente con diabetes gestacional de 28 semanas con mal control glucémico"

2. **Gemini Flash extracts**:
   ```json
   {
     "keywords": ["gestational diabetes", "pregnancy", "third trimester", "glycemic control"],
     "mesh_terms": ["diabetes, gestational[mesh]", "pregnancy trimester, third[mesh]", "blood glucose[mesh]"],
     "suggested_query": "diabetes, gestational[mesh] AND pregnancy trimester, third[mesh] AND blood glucose[mesh]"
   }
   ```

3. **PubMed search**: Uses optimized English query
4. **Results**: High-quality, relevant scientific articles

**Benefits**:
- Better PubMed results
- Proper MeSH term usage
- Language-agnostic system
- Evidence-based responses

---

## 🚀 Performance Optimizations

### **1. Parallel Specialist Execution**

**Before** (sequential):
```python
for specialist in specialists:
    result = await specialist.process()  # 30s each
# Total: 90s for 3 specialists
```

**After** (parallel):
```python
tasks = [specialist.process() for specialist in specialists]
results = await asyncio.gather(*tasks)  # All at once
# Total: 30s for 3 specialists
```

**Improvement**: 3x faster

### **2. Caching Strategy**

**RAG Embeddings**: ChromaDB caches embeddings
**PubMed Results**: Could add Redis cache (future)
**Gemini Responses**: No caching (medical accuracy priority)

### **3. Database Indexes**

```python
# MongoDB indexes for fast queries
MedicalConsultation.create_indexes([
    IndexModel([("user_id", 1)]),
    IndexModel([("estado", 1)]),
    IndexModel([("timestamp", -1)])
])
```

---

## 🔍 Debugging and Monitoring

### **Execution Trace**

Every workflow step is logged in MongoDB:

```python
{
  "execution_trace": [
    {
      "step": "evaluate_consultation",
      "timestamp": "2025-01-08T10:30:00Z",
      "data": {
        "can_answer_directly": false,
        "specialists": ["endocrinology", "pharmacology"]
      }
    },
    {
      "step": "execute_specialists",
      "timestamp": "2025-01-08T10:31:00Z",
      "data": {
        "count": 2,
        "duration_seconds": 28
      }
    }
  ]
}
```

### **Logging**

**Location**: Throughout the codebase

```python
print("🩺 GP: Evaluating consultation...")
print("📋 GP: Generating interconsultation notes...")
print("🔬 Executing specialist consultations in parallel...")
print("  → Endocrinology: Processing...")
print("  ✓ Endocrinology: Response received")
```

### **Health Checks**

```bash
# API health
curl http://localhost:8000/health

# MongoDB
mongosh --eval "db.adminCommand('ping')"

# ChromaDB
ls -la data/vectorstore/
```

---

## 📚 Adding New Specialists

### **Step-by-Step Guide**

**1. Create configuration in `app/config/specialists.yaml`**:

```yaml
specialists:
  neurology:
    name: "Neurology"
    description: "Specialist in nervous system diseases"
    model: "models/gemini-2.5-pro"
    temperature: 0.05
    rag_collection: "neurology_kb"
    enabled: true

    tools:
      - pubmed_search
      - rag_search
      - neurological_scales

    system_prompt: |
      You are an expert neurologist...

    expert_topics:
      - Stroke
      - Epilepsy
      - Movement disorders
      - Dementia
```

**2. Add knowledge base documents**:

```bash
mkdir -p data/knowledge_base/neurology
# Add PDFs, DOCX, MD files
cp stroke_guidelines.pdf data/knowledge_base/neurology/
```

**3. Index documents**:

```bash
python -m app.rag.document_indexer --specialty neurology
```

**4. (Optional) Create custom specialist class**:

```python
# app/agents/specialists/neurology.py
from app.agents.specialists.base import SpecialistAgent

class NeurologySpecialist(SpecialistAgent):
    def __init__(self):
        super().__init__(specialty="neurology")

    async def calculate_nihss(self, patient_data):
        """Calculate NIH Stroke Scale"""
        # Custom neurology-specific logic
        pass
```

**5. Register in `app/agents/specialists/__init__.py`**:

```python
from app.agents.specialists.neurology import NeurologySpecialist

SPECIALIST_AGENTS = {
    "cardiology": cardiology_agent,
    "endocrinology": endocrinology_agent,
    "pharmacology": pharmacology_agent,
    "neurology": NeurologySpecialist(),  # Add new specialist
}
```

**Done!** The system will automatically use the new specialist when needed.

---

## 🎓 Learning Resources

### **Understanding LangGraph**

LangGraph is a state machine framework for building multi-agent systems:

- **Nodes**: Functions that process state
- **Edges**: Transitions between nodes
- **State**: Data passed through workflow
- **Conditional edges**: Dynamic routing based on state

### **Understanding RAG**

RAG enhances LLM responses with external knowledge:

1. **Retrieve**: Find relevant documents
2. **Augment**: Add documents to prompt
3. **Generate**: LLM creates informed response

### **Understanding Async/Await**

Python async enables non-blocking I/O:

```python
# Blocking (slow)
def get_data():
    return api_call()  # Waits

# Non-blocking (fast)
async def get_data():
    return await api_call()  # Can do other work while waiting
```

---

## 📊 System Metrics

**Typical Performance**:
- Simple consultation (GP only): ~5-10 seconds
- Complex consultation (2 specialists): ~30-40 seconds
- Complex consultation (3+ specialists): ~30-50 seconds (parallel execution)

**Resource Usage**:
- MongoDB: ~100MB for 1000 consultations
- ChromaDB: ~500MB per specialty (depends on knowledge base size)
- Gemini API: ~10-20 tokens per request

---

## 🔐 Security Considerations

**Current State** (Development):
- No authentication
- No rate limiting
- No data encryption

**Production Requirements**:
- User authentication (JWT)
- API rate limiting
- MongoDB encryption at rest
- HTTPS/TLS for API
- HIPAA/GDPR compliance
- Audit logging
- PHI (Protected Health Information) handling

---

## 🌟 Future Enhancements

**Planned Features**:
1. **More specialists**: Neurology, Psychiatry, Obstetrics, Pediatrics
2. **Real-time streaming**: WebSocket support for live responses
3. **Multi-language support**: Full English interface
4. **Image analysis**: Medical image interpretation
5. **FHIR integration**: Interoperability with EHR systems
6. **Clinical decision support**: Alerts, drug interactions
7. **Analytics dashboard**: Usage metrics, performance monitoring

---

## 📝 Summary

**Clinical Crew** is a sophisticated multi-agent medical consultation system that:

1. **Receives** Spanish medical questions from doctors
2. **Routes** complex cases to specialist AI agents
3. **Searches** local knowledge bases (RAG) and scientific literature (PubMed)
4. **Processes** specialist consultations in parallel for speed
5. **Integrates** responses into comprehensive clinical records
6. **Generates** evidence-based therapeutic plans

**Key Technologies**:
- **LangGraph**: Multi-agent orchestration
- **Google Gemini**: LLM for medical reasoning
- **ChromaDB**: Vector database for RAG
- **MongoDB**: Document storage
- **FastAPI**: REST API framework
- **Biopython**: PubMed integration

**Architecture Highlights**:
- Bilingual (Spanish input/output, English processing)
- Parallel specialist execution
- RAG-enhanced responses
- Intelligent keyword extraction
- Structured medical note generation
- Complete audit trail

---

**For more details, see**:
- `CLAUDE.md` - Development guidelines
- `README.md` - Project overview
- `docs/` - API examples and tutorials
