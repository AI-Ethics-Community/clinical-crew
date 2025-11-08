"""
Base class for medical specialist agents.
"""
import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from app.services.gemini_client import gemini_especialista
from app.services.pubmed_client import pubmed_client
from app.rag.retriever import retriever
from app.agents.prompts.specialists import get_prompt_especialista
from app.models.consultation import CounterReferralNote, PatientContext
from app.models.notes import FormatoContextoPaciente
from app.config.settings import settings


class SpecialistAgent:
    """Base class for all medical specialist agents"""

    def __init__(self, specialty: str):
        """
        Initialize the specialist agent.

        Args:
            specialty: Medical specialty name
        """
        self.specialty = specialty
        self.config = self._load_config()
        self.gemini_client = gemini_especialista

    def _load_config(self) -> Dict[str, Any]:
        """
        Load specialist configuration from YAML.

        Returns:
            Specialist configuration
        """
        config_path = Path(settings.especialistas_config_path)

        with open(config_path, 'r', encoding='utf-8') as f:
            all_config = yaml.safe_load(f)

        specialty_key = self.specialty.lower()
        if specialty_key not in all_config.get('specialists', {}):
            raise ValueError(f"Specialty not found in config: {self.specialty}")

        return all_config['specialists'][specialty_key]

    async def process_interconsulta(
        self,
        interconsulta_id: str,
        pregunta: str,
        contexto: Dict[str, Any],
        patient_context: PatientContext
    ) -> CounterReferralNote:
        """
        Process an interconsultation request.

        Args:
            interconsulta_id: ID of the interconsultation
            pregunta: Specific question from general practitioner
            contexto: Relevant context for this specialty
            patient_context: Full patient context

        Returns:
            Counter-referral note with specialist's response
        """
        # Step 1: Retrieve from RAG knowledge base
        rag_context = await self._retrieve_from_rag(pregunta)

        # Step 2: Search PubMed if needed
        pubmed_context = await self._search_pubmed(pregunta)

        # Step 3: Generate response with Gemini
        response = await self._generate_response(
            pregunta=pregunta,
            contexto=contexto,
            patient_context=patient_context,
            rag_context=rag_context,
            pubmed_context=pubmed_context
        )

        # Step 4: Parse and create counter-referral
        counter_referral = self._create_contrarreferencia(
            interconsulta_id=interconsulta_id,
            response_data=response
        )

        return counter_referral

    async def _retrieve_from_rag(self, pregunta: str, top_k: int = 5) -> str:
        """
        Retrieve relevant information from RAG knowledge base.

        Args:
            pregunta: Question to search for
            top_k: Number of results to retrieve

        Returns:
            Formatted context from RAG
        """
        try:
            result = retriever.retrieve_with_context(
                query=pregunta,
                specialty=self.specialty,
                top_k=top_k,
                include_sources=True
            )
            return result['context']
        except Exception as e:
            print(f"Error retrieving from RAG: {str(e)}")
            return "No additional information found in knowledge base."

    async def _search_pubmed(
        self,
        pregunta: str,
        max_results: int = 5
    ) -> str:
        """
        Search PubMed for relevant articles.

        Args:
            pregunta: Question to search for
            max_results: Maximum number of articles

        Returns:
            Formatted articles from PubMed
        """
        try:
            # Build search query
            query = f"{pregunta} {self.specialty}"

            # Search with cache
            articles = await pubmed_client.search_with_cache(
                query=query,
                specialty=self.specialty,
                max_results=max_results
            )

            # Format for context
            return pubmed_client.format_articles_for_context(articles)

        except Exception as e:
            print(f"Error searching PubMed: {str(e)}")
            return "No articles found in PubMed."

    async def _generate_response(
        self,
        pregunta: str,
        contexto: Dict[str, Any],
        patient_context: PatientContext,
        rag_context: str,
        pubmed_context: str
    ) -> Dict[str, Any]:
        """
        Generate response using Gemini.

        Args:
            pregunta: Specific question
            contexto: Relevant context
            patient_context: Patient context
            rag_context: Context from RAG
            pubmed_context: Context from PubMed

        Returns:
            Parsed response data
        """
        # Format patient context
        contexto_paciente_str = FormatoContextoPaciente.formatear(
            patient_context.model_dump()
        )

        # Format interconsultation context
        contexto_str = json.dumps(contexto, indent=2, ensure_ascii=False)

        # Get system instruction from config
        system_instruction = self.config.get('prompt_sistema', '')

        # Build prompt
        prompt = get_prompt_especialista(
            specialty=self.specialty,
            system_instruction=system_instruction,
            pregunta=pregunta,
            contexto=contexto_str,
            patient_context=contexto_paciente_str,
            rag_context=rag_context,
            pubmed_context=pubmed_context
        )

        # Generate with Gemini
        response_text = await self.gemini_client.generate_content_async(prompt)

        # Parse JSON response
        response_data = self._parse_json_response(response_text)

        return response_data

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM.

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON data
        """
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            else:
                json_str = response_text.strip()

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {str(e)}")
            print(f"Response text: {response_text}")

            # Fallback: return a structured error response
            return {
                "evaluacion": "Error parsing specialist response",
                "evidence_used": [],
                "clinical_reasoning": response_text,
                "respuesta": "Error generating structured response",
                "recomendaciones": [],
                "evidence_level": "Unknown",
                "requires_additional_info": False,
                "additional_questions": []
            }

    def _create_contrarreferencia(
        self,
        interconsulta_id: str,
        response_data: Dict[str, Any]
    ) -> CounterReferralNote:
        """
        Create counter-referral note from response data.

        Args:
            interconsulta_id: ID of the interconsultation
            response_data: Parsed response from Gemini

        Returns:
            Counter-referral note
        """
        return CounterReferralNote(
            interconsulta_id=interconsulta_id,
            specialty=self.specialty,
            evaluacion=response_data.get('evaluacion', ''),
            evidence_used=response_data.get('evidence_used', []),
            clinical_reasoning=response_data.get('clinical_reasoning', ''),
            respuesta=response_data.get('respuesta', ''),
            recomendaciones=response_data.get('recomendaciones', []),
            evidence_level=response_data.get('evidence_level', 'Unknown'),
            requires_additional_info=response_data.get('requires_additional_info', False),
            additional_questions=response_data.get('additional_questions', [])
        )
