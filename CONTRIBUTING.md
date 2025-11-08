# Contributing to Clinical Crew

Thank you for your interest in contributing to Clinical Crew!

## Development Setup

1. Fork the repository
2. Clone your fork:

   ```bash
   git clone https://github.com/your-username/ClinicalCrew.git
   cd ClinicalCrew
   ```

3. Run the quickstart script:

   ```bash
   ./quickstart.sh
   ```

4. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Code Style

- Follow PEP 8 for Python code
- Use type hints
- Write docstrings for all functions and classes
- Keep code in English (variables, comments, documentation)
- Use descriptive variable names

## Adding a New Medical Specialist

1. Create specialist file in `app/agents/specialists/`:

   ```python
   # app/agents/specialists/neurology.py
   from app.agents.specialists.base import SpecialistAgent

   class NeurologyAgent(SpecialistAgent):
       def __init__(self):
           super().__init__(specialty="neurology")

   neurology_agent = NeurologyAgent()
   ```

2. Add configuration in `app/config/specialists.yaml`:

   ```yaml
   neurology:
     name: "Neurology"
     description: "Specialist in nervous system diseases"
     model: "gemini-2.5-flash-latest"
     temperature: 0.1
     rag_collection: "neurology_kb"
     enabled: true

     tools:
       - pubmed_search
       - rag_search

     system_prompt: |
       You are an expert neurologist...

     expert_topics:
       - Stroke
       - Epilepsy
       - Movement disorders
   ```

3. Add prompts in `app/agents/prompts/specialists.py`:

   ```python
   PROMPT_NEUROLOGY = """
   Your approach should be based on:
   - Neurology clinical guidelines
   - Evidence-based protocols
   ...
   """

   PROMPTS_SPECIALTY["neurology"] = PROMPT_NEUROLOGY
   ```

4. Update `app/agents/specialists/__init__.py`:

   ```python
   from app.agents.specialists.neurology import NeurologyAgent, neurology_agent

   SPECIALIST_AGENTS = {
       "cardiology": cardiology_agent,
       "endocrinology": endocrinology_agent,
       "pharmacology": pharmacology_agent,
       "neurology": neurology_agent,  # Add new specialist
   }
   ```

5. Add knowledge base documents in `data/knowledge_base/neurology/`

6. Index documents:
   ```bash
   python -m app.rag.document_indexer --specialty neurology
   ```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_agents/test_specialists.py
```

## Code Quality

Before submitting a PR:

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Check style
flake8 app/ tests/

# Type checking
mypy app/
```

## Documentation

- Update docstrings for any new functions
- Update README.md if adding major features
- Add examples in `docs/` if appropriate
- Update API documentation in `docs/api_examples.md`

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update `CHANGELOG.md` with your changes
5. Submit PR with clear description:
   - What does this PR do?
   - Why is this change needed?
   - How has it been tested?

## Commit Messages

Follow conventional commits:

```
feat: add neurology specialist
fix: correct drug interaction detection
docs: update API examples
test: add tests for RAG retriever
refactor: simplify consultation workflow
```

## Questions or Issues?

- Open an issue for bugs or feature requests
- Use discussions for questions
- Tag maintainers for urgent issues

## Code of Conduct

Be respectful and constructive in all interactions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
