# Agent Cards Documentation

## Overview

Clinical Crew implements the **Agent Cards** documentation standard for operational AI agents, as proposed by Urteaga-Reyesvera & Lopez Murphy (2025) and accepted at MICAI 2025 Workshops.

Agent Cards provide a lightweight, structured standard for documenting AI agents — covering their behavioral attributes, memory design, tool integrations, communication protocols, and governance metadata.

## What are Agent Cards?

Agent Cards extend the model-centric transparency artifacts (Model Cards, FactSheets) into the agentic AI era, supporting reproducibility, comparability, and governance of autonomous and multi-agent systems.

**Publication**: MICAI 2025 Workshops (Lecture Notes in Artificial Intelligence)
**Publisher**: Springer Nature Switzerland AG
**Repository**: https://github.com/CarlosUrteaga/agentcard
**License**: MIT

## Agent Cards in Clinical Crew

### Agents with Agent Cards

Clinical Crew has Agent Cards for all operational agents:

1. **General Practitioner Agent** (`general_practitioner.yaml`)
   - Role: Medical Coordinator, Initial Evaluator, Interconsultation Orchestrator, Response Integrator
   - LLM: Google Gemini Pro (models/gemini-2.5-pro) @ Temperature 0.1
   - Tools: Gemini API, Interrogation System, Interconsultation Generator, Response Integrator

2. **Cardiology Specialist Agent** (`cardiology.yaml`)
   - Role: Medical Specialist, Evidence Synthesizer, Clinical Advisor
   - LLM: Google Gemini Pro (models/gemini-2.5-pro) @ Temperature 0.05
   - Tools: RAG (cardiology_kb), PubMed Search, Keyword Extractor, Gemini API
   - Expert Topics: Heart failure, Ischemic heart disease, Arrhythmias, Valvular disease, Hypertension, Cardiomyopathies

3. **Endocrinology Specialist Agent** (`endocrinology.yaml`)
   - Role: Medical Specialist, Evidence Synthesizer, Clinical Advisor
   - LLM: Google Gemini Pro (models/gemini-2.5-pro) @ Temperature 0.05
   - Tools: RAG (endocrinology_kb), PubMed Search, Keyword Extractor, Gemini API
   - Expert Topics: Diabetes mellitus, Thyroid disorders, Adrenal disorders, Osteoporosis, Metabolic syndrome

4. **Clinical Pharmacology Specialist Agent** (`pharmacology.yaml`)
   - Role: Medical Specialist, Evidence Synthesizer, Clinical Advisor, Drug Safety Expert
   - LLM: Google Gemini Pro (models/gemini-2.5-pro) @ Temperature 0.05
   - Tools: RAG (pharmacology_kb), PubMed Search, Keyword Extractor, Drug Database, Gemini API
   - Expert Topics: Drug interactions, Pharmacology in special populations, Adverse reactions, Dose adjustment

## Agent Card Structure

Each Agent Card contains the following sections:

### Core Metadata
- **meta**: Agent name, version, owner, repository, license, last updated
- **purpose**: Objective, users, domain
- **agent_version**: Semantic version
- **agent_name**: Class name
- **agent_role**: List of roles (Coordinator, Specialist, Advisor, etc.)

### Operational Specifications
- **interface**: Inputs and outputs
- **memory**: Short-term and long-term memory architecture
- **tools_functions**: Available tools, their purpose, scope, and eligibility
- **autonomy**: Allowed actions, approval requirements, deference policies
- **communication**: Human interfaces, agent-to-agent protocols, handoff policies

### Governance & Safety
- **monitoring**: Logged metrics, trace systems, observability
- **governance**: Safety filters, data handling (PII/PHI), compliance standards, prohibited actions
- **versioning**: Release information, model versions, dependencies
- **known_limitations**: Scope boundaries, partial automation, brittleness sources

### Quality Assurance
- **evaluation**: Benchmarks, KPIs, calibration policies, evaluation datasets
- **risks**: Risk name, severity, mitigation strategies
- **ethical_considerations**: Ethical guidelines and considerations

### LLM Configuration
Each Agent Card documents:
- **Model name**: e.g., "models/gemini-2.5-pro"
- **Model version**: e.g., "Google Gemini Pro"
- **Temperature**: e.g., 0.05 for specialists, 0.1 for GP
- **Purpose**: What the LLM is used for
- **Scope**: Medical reasoning, clinical decision-making, etc.

## Using Agent Cards in Code

### Initialization

Agent Cards are automatically loaded during application startup:

```python
from app.core.agentcard_loader import initialize_agentcards

# In app/main.py lifespan
initialize_agentcards()
```

### Accessing Agent Cards

```python
from app.core.agentcard_loader import get_agent_card, get_agent_llm_config

# Get full Agent Card
card = get_agent_card("cardiology")

# Get LLM configuration
llm_config = get_agent_llm_config("cardiology")
print(f"Model: {llm_config['model_name']}")
print(f"Temperature: {llm_config['temperature']}")
```

### Agent Integration

Agents automatically load their Agent Cards during initialization:

```python
class SpecialistAgent:
    def __init__(self, specialty: str, ...):
        self.specialty = specialty

        # Load Agent Card
        self.agent_card = get_agent_card(specialty)
        self.llm_config = get_agent_llm_config(specialty)
```

### Agent Card Registry

The `AgentCardRegistry` class provides centralized access:

```python
from app.core.agentcard_loader import agentcard_registry

# List all loaded cards
cards = agentcard_registry.list_loaded_cards()

# Get agent metadata
metadata = agentcard_registry.get_agent_metadata("cardiology")

# Get agent tools
tools = agentcard_registry.get_agent_tools("endocrinology")

# Get agent risks
risks = agentcard_registry.get_agent_risks("pharmacology")

# Export summary
summary = agentcard_registry.export_card_summary("general_practitioner")
print(summary)
```

## Key Features Documented

### 1. Multi-Agent Orchestration
- LangGraph state machine workflow
- Parallel specialist execution via `asyncio.gather`
- Event-driven communication (EventEmitter)
- Stateless specialist agents for parallelization

### 2. Medical Knowledge Integration
- RAG (Retrieval-Augmented Generation) with ChromaDB
- PubMed literature search with bilingual support
- Spanish → English MeSH term translation
- Evidence-based medicine with source citations

### 3. Safety & Governance
- **Critical Rule**: DO NOT FABRICATE DATA
- `requires_additional_info` flag when data is missing
- Evidence level classification (High/Medium/Low)
- Human-in-the-loop checkpoints
- Audit trails via execution_trace

### 4. Observability
- Real-time event streaming (SSE)
- Consultation-specific logging
- Tool execution monitoring (RAG, PubMed, LLM)
- Source tracking (SourceFoundEvent)

## Agent Card Compliance

All Clinical Crew agents comply with the Agent Card standard:

✅ **Metadata**: Complete version, owner, license information
✅ **Purpose**: Clear objective and user specification
✅ **Tools**: Detailed tool documentation with scope and eligibility
✅ **Autonomy**: Explicit allowed actions and approval requirements
✅ **Memory**: Short-term and long-term memory architecture
✅ **Communication**: Agent-to-agent and human interface protocols
✅ **Monitoring**: Logged metrics and observability
✅ **Governance**: Safety filters, data handling, compliance
✅ **Versioning**: Model versions, dependencies, release information
✅ **Evaluation**: KPIs, benchmarks, calibration policies
✅ **Risks**: Identified risks with mitigation strategies
✅ **Ethics**: Ethical considerations and guidelines

## Benefits of Agent Cards

1. **Transparency**: Clear documentation of agent capabilities and limitations
2. **Reproducibility**: Complete versioning information for agent recreation
3. **Governance**: Explicit safety policies and compliance standards
4. **Risk Management**: Identified risks with mitigation strategies
5. **Evaluation**: Standardized benchmarks and KPIs
6. **Interoperability**: Standard format for multi-agent systems
7. **Auditability**: Complete operational specifications
8. **Ethical Clarity**: Explicit ethical considerations and constraints

## Viewing Agent Cards

Agent Card YAML files are located in:
```
app/config/agentcards/
├── general_practitioner.yaml
├── cardiology.yaml
├── endocrinology.yaml
└── pharmacology.yaml
```

You can view them directly or use the registry:

```bash
# View a specific Agent Card
cat app/config/agentcards/cardiology.yaml

# Or use Python
python3 -c "
from app.core.agentcard_loader import agentcard_registry
agentcard_registry.load_all_cards()
print(agentcard_registry.export_card_summary('cardiology'))
"
```

## Adding New Agents

When adding a new specialist agent:

1. Create Agent Card YAML in `app/config/agentcards/{specialty}.yaml`
2. Follow the Agent Card template structure
3. Document all tools, risks, and governance policies
4. Add specialist configuration to `app/config/specialists.yaml`
5. Agent Card will be automatically loaded on startup

## Citation

If you use Clinical Crew's Agent Card implementation, please cite:

**Agent Card Standard:**
```
Urteaga-Reyesvera, J. C., & Lopez Murphy, J. J. (2025).
Agent Cards: A Documentation Standard for Operational AI Agents.
In MICAI 2025 Workshops (Lecture Notes in Artificial Intelligence).
Springer Nature Switzerland AG.
https://github.com/CarlosUrteaga/agentcard
```

**Clinical Crew:**
```
AI Ethics Community. (2025). Clinical Crew: Multi-Agent Medical Consultation System.
https://github.com/AI-Ethics-Community/clinical-crew
```

## References

- **Agent Card Repository**: https://github.com/CarlosUrteaga/agentcard
- **Agent Card Standard**: MICAI 2025 Workshops (Forthcoming)
- **Clinical Crew Repository**: https://github.com/AI-Ethics-Community/clinical-crew
- **License**: BSD-2-Clause (Clinical Crew), MIT (Agent Card Standard)

## Support

For questions about Agent Cards in Clinical Crew:
- Open an issue: https://github.com/AI-Ethics-Community/clinical-crew/issues
- See Agent Card standard: https://github.com/CarlosUrteaga/agentcard

---

**Note**: Agent Cards are a living document. They should be updated whenever agent capabilities, tools, or governance policies change.
