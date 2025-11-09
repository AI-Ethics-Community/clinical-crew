"""
Base class for medical specialist agents.
"""
import json
import yaml
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from app.services.gemini_client import gemini_especialista
from app.services.pubmed_client import pubmed_client
from app.rag.retriever import retriever
from app.services.file_search_service import file_search_service
from app.agents.prompts.specialists import get_prompt_especialista
from app.models.consultation import CounterReferralNote, PatientContext
from app.models.sources import ScientificSource, SourceType
from app.models.notes import FormatoContextoPaciente
from app.config.settings import settings
from app.core.agentcard_loader import get_agent_card, get_agent_llm_config


class SpecialistAgent:
    """Base class for all medical specialist agents"""

    def __init__(
        self,
        specialty: str,
        on_tool_start: Optional[Callable] = None,
        on_tool_complete: Optional[Callable] = None,
        on_source_found: Optional[Callable] = None
    ):
        """
        Initialize the specialist agent.

        Args:
            specialty: Medical specialty name
            on_tool_start: Callback when a tool starts
            on_tool_complete: Callback when a tool completes
            on_source_found: Callback when a source is found
        """
        self.specialty = specialty
        self.config = self._load_config()
        self.gemini_client = gemini_especialista
        self.sources: List[ScientificSource] = []
        self.on_tool_start = on_tool_start
        self.on_tool_complete = on_tool_complete
        self.on_source_found = on_source_found

        # Load Agent Card
        self.agent_card = get_agent_card(specialty)
        self.llm_config = get_agent_llm_config(specialty)

        if self.agent_card:
            print(f"  ✓ Agent Card loaded for {specialty}")
        if self.llm_config:
            print(f"    LLM: {self.llm_config.get('model_name', 'Unknown')} @ T={self.llm_config.get('temperature', 'Unknown')}")

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

    async def process_interconsultation(
        self,
        interconsultation_id: str,
        question: str,
        context: Dict[str, Any],
        patient_context: PatientContext
    ) -> CounterReferralNote:
        """
        Process an interconsultation request.

        Args:
            interconsultation_id: ID of the interconsultation
            question: Specific question from general practitioner
            context: Relevant context for this specialty
            patient_context: Full patient context

        Returns:
            Counter-referral note with specialist's response
        """
        self.sources = []

        if self.on_tool_start:
            await self.on_tool_start("rag_retrieval", self.specialty)
        rag_context = await self._retrieve_from_rag(question)
        if self.on_tool_complete:
            await self.on_tool_complete("rag_retrieval", self.specialty)

        if self.on_tool_start:
            await self.on_tool_start("pubmed_search", self.specialty)
        pubmed_context = await self._search_pubmed(question)
        if self.on_tool_complete:
            await self.on_tool_complete("pubmed_search", self.specialty)

        if self.on_tool_start:
            await self.on_tool_start("response_generation", self.specialty)
        response = await self._generate_response(
            question=question,
            context=context,
            patient_context=patient_context,
            rag_context=rag_context,
            pubmed_context=pubmed_context
        )
        if self.on_tool_complete:
            await self.on_tool_complete("response_generation", self.specialty)

        counter_referral = self._create_counter_referral(
            interconsultation_id=interconsultation_id,
            response_data=response
        )

        return counter_referral

    async def _retrieve_from_rag(self, question: str, top_k: Optional[int] = None) -> str:
        """
        Retrieve relevant information from RAG knowledge base.
        Uses Gemini File Search if configured, otherwise falls back to ChromaDB.

        Args:
            question: Question to search for
            top_k: Number of results to retrieve (uses settings default if None)

        Returns:
            Formatted context from RAG
        """
        try:
            if top_k is None:
                top_k = settings.rag_top_k

            # Use File Search if configured
            if settings.use_file_search:
                return await self._retrieve_from_file_search(question, top_k)

            # Fallback to ChromaDB
            result = retriever.retrieve_with_context(
                query=question,
                specialty=self.specialty,
                top_k=top_k,
                include_sources=True
            )

            # Filter sources by minimum relevance score
            if 'sources' in result:
                filtered_sources = []
                for source_dict in result['sources']:
                    score = source_dict.get('score', 0.0)

                    # Apply relevance threshold
                    if score < settings.rag_min_relevance_score:
                        print(f"⏭️  Skipped low-relevance source: {source_dict.get('title')} (score: {score:.3f})")
                        continue

                    source = ScientificSource(
                        source_type=SourceType.RAG,
                        title=source_dict.get('title', 'Unknown'),
                        content=source_dict.get('content', ''),
                        metadata=source_dict.get('metadata', {})
                    )
                    filtered_sources.append(source)
                    self.sources.append(source)

                    if self.on_source_found:
                        await self.on_source_found(source)

                # Log score distribution for monitoring
                if filtered_sources:
                    scores = [s.metadata.get('score', 0.0) for s in filtered_sources]
                    print(f"✓ Retrieved {len(filtered_sources)} RAG sources (filtered from {len(result.get('sources', []))} by min_score={settings.rag_min_relevance_score})")
                    print(f"  📊 Score range: {min(scores):.3f}-{max(scores):.3f}, avg: {sum(scores)/len(scores):.3f}")
                else:
                    print(f"⚠️  Retrieved 0 RAG sources after filtering (min_score={settings.rag_min_relevance_score})")

                # Adaptive retrieval: if very few sources, retry with lower threshold
                if len(filtered_sources) < 2 and settings.rag_min_relevance_score > 0.25:
                    print(f"⚠️  Only {len(filtered_sources)} sources found, retrying with lower threshold (0.25)...")

                    # Retry with lower threshold
                    retry_result = retriever.retrieve_with_context(
                        query=question,
                        specialty=self.specialty,
                        top_k=top_k,
                        include_sources=True
                    )

                    # Filter with lower threshold
                    if 'sources' in retry_result:
                        additional_sources = []
                        for source_dict in retry_result['sources']:
                            score = source_dict.get('score', 0.0)

                            # Use lower threshold (0.25) but exclude already added sources
                            if score >= 0.25 and score < settings.rag_min_relevance_score:
                                source = ScientificSource(
                                    source_type=SourceType.RAG,
                                    title=source_dict.get('title', 'Unknown'),
                                    content=source_dict.get('content', ''),
                                    metadata=source_dict.get('metadata', {})
                                )
                                additional_sources.append(source)
                                self.sources.append(source)

                                if self.on_source_found:
                                    await self.on_source_found(source)

                        if additional_sources:
                            print(f"  ✓ Added {len(additional_sources)} additional sources with scores 0.25-{settings.rag_min_relevance_score:.2f}")

            return result['context']
        except Exception as e:
            print(f"Error retrieving from RAG: {str(e)}")
            import traceback
            traceback.print_exc()
            return "No additional information found in knowledge base."

    async def _retrieve_from_file_search(self, question: str, top_k: int) -> str:
        """
        Retrieve relevant information using Gemini File Search.

        File Search works differently than ChromaDB - the LLM automatically
        searches the store and returns grounded responses with citations.

        Args:
            question: Question to search for
            top_k: Number of results (note: File Search determines actual count)

        Returns:
            Formatted context from File Search
        """
        try:
            # Use File Search to generate context
            # The LLM will automatically search and ground its response
            search_query = f"Busca información relevante sobre: {question}"

            response_text, citations = file_search_service.generate_with_file_search(
                query=search_query,
                specialty=self.specialty,
                system_instruction="Eres un asistente médico que busca información relevante en guías clínicas. Proporciona un resumen conciso de la información encontrada."
            )

            # Process citations as sources
            if citations:
                for citation in citations:
                    score = citation.score

                    # Filter by threshold
                    if score < settings.rag_min_relevance_score:
                        print(f"⏭️  Skipped low-relevance citation: {citation.metadata.get('filename')} (score: {score:.3f})")
                        continue

                    source = ScientificSource(
                        source_type=SourceType.RAG,
                        title=citation.metadata.get('filename', 'Unknown'),
                        content=citation.content,
                        metadata=citation.metadata
                    )
                    self.sources.append(source)

                    if self.on_source_found:
                        await self.on_source_found(source)

                # Log statistics
                filtered_count = len([c for c in citations if c.score >= settings.rag_min_relevance_score])
                if filtered_count > 0:
                    scores = [c.score for c in citations if c.score >= settings.rag_min_relevance_score]
                    print(f"✓ Retrieved {filtered_count} File Search citations (min_score={settings.rag_min_relevance_score})")
                    print(f"  📊 Score range: {min(scores):.3f}-{max(scores):.3f}, avg: {sum(scores)/len(scores):.3f}")
                else:
                    print(f"⚠️  Retrieved 0 File Search citations after filtering (min_score={settings.rag_min_relevance_score})")

            # Format the response as context
            if response_text:
                return f"Información de la base de conocimiento:\n\n{response_text}"
            else:
                return "No se encontró información relevante en la base de conocimiento."

        except Exception as e:
            print(f"Error retrieving from File Search: {str(e)}")
            import traceback
            traceback.print_exc()
            return "No additional information found in knowledge base."

    async def _search_pubmed(
        self,
        question: str,
        max_results: int = 5
    ) -> str:
        """
        Search PubMed for relevant articles using keyword extraction.

        Args:
            question: Medical question to search for
            max_results: Maximum number of articles

        Returns:
            Formatted articles from PubMed
        """
        try:
            # Step 1: Extract medical keywords from Spanish question
            if settings.pubmed_use_mesh_extraction:
                print(f"💡 Extracting medical keywords for PubMed search...")
                try:
                    keywords_data = await pubmed_client.extract_medical_keywords_async(
                        question, self.specialty
                    )
                except Exception as e:
                    print(f"⚠ Keyword extraction failed: {str(e)}. Using specialty fallback.")
                    # Fallback to simple specialty search
                    keywords_data = {
                        "keywords": [self.specialty],
                        "mesh_terms": [],
                        "suggested_query": self.specialty
                    }
            else:
                # Keyword extraction disabled
                keywords_data = {
                    "keywords": [self.specialty],
                    "mesh_terms": [],
                    "suggested_query": self.specialty
                }
            
            # Step 2: Build MeSH query with date range
            query = pubmed_client.build_mesh_query(
                keywords_data,
                min_year=settings.pubmed_min_year,
                max_year=settings.pubmed_max_year
            )
            
            if not query:
                print("⚠ Could not build query from keywords")
                return "No articles found in PubMed."
            
            print(f"🔍 Final PubMed query: {query}")
            
            # Step 3: Search with retry logic
            print(f"🔍 Searching PubMed: {query[:80]}...")
            pmids = pubmed_client.search_with_retry(
                query=query,
                max_results=max_results
            )
            
            if not pmids:
                print("⚠ No articles found")
                return "No relevant articles found in PubMed for this query."
            
            articles = pubmed_client.fetch_details(pmids)

            if not articles:
                print("⚠ Could not fetch article details")
                return "No articles found in PubMed."

            for article in articles:
                source = ScientificSource(
                    source_type=SourceType.PUBMED,
                    title=article.get('title', 'Unknown'),
                    content=article.get('abstract', ''),
                    pmid=article.get('pmid'),
                    doi=article.get('doi'),
                    authors=article.get('authors', []),
                    journal=article.get('journal'),
                    publication_date=article.get('publication_date'),
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid')}/" if article.get('pmid') else None
                )
                self.sources.append(source)
                if self.on_source_found:
                    await self.on_source_found(source)

            print(f"✓ Retrieved {len(articles)} PubMed articles")
            return pubmed_client.format_articles_for_context(articles)

        except Exception as e:
            error_msg = str(e)
            print(f"✗ Error in PubMed search: {error_msg}")

            # Log the error for visibility
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"PubMed search failed for specialty {self.specialty}: {error_msg}")

            # Return informative message
            return f"PubMed search unavailable due to: {error_msg[:100]}"

    async def _generate_response(
        self,
        question: str,
        context: Dict[str, Any],
        patient_context: PatientContext,
        rag_context: str,
        pubmed_context: str
    ) -> Dict[str, Any]:
        """
        Generate response using Gemini.

        Args:
            question: Specific question
            context: Relevant context
            patient_context: Patient context
            rag_context: Context from RAG
            pubmed_context: Context from PubMed

        Returns:
            Parsed response data
        """
        # Format patient context
        patient_context_str = FormatoContextoPaciente.formatear(
            patient_context.model_dump()
        )

        # Format interconsultation context
        context_str = json.dumps(context, indent=2, ensure_ascii=False)

        # Get system instruction from config
        system_instruction = self.config.get('system_prompt', '')

        # Build prompt
        prompt = get_prompt_especialista(
            specialty=self.specialty,
            system_instruction=system_instruction,
            question=question,
            context=context_str,
            patient_context=patient_context_str,
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
                "evaluation": "Error parsing specialist response",
                "evidence_used": [],
                "clinical_reasoning": response_text,
                "response": "Error generating structured response",
                "recommendations": [],
                "evidence_level": "Unknown",
                "requires_additional_info": False,
                "additional_questions": []
            }

    def _create_counter_referral(
        self,
        interconsultation_id: str,
        response_data: Dict[str, Any]
    ) -> CounterReferralNote:
        """
        Create counter-referral note from response data.

        Args:
            interconsultation_id: ID of the interconsultation
            response_data: Parsed response from Gemini

        Returns:
            Counter-referral note
        """
        return CounterReferralNote(
            interconsultation_id=interconsultation_id,
            specialty=self.specialty,
            evaluation=response_data.get('evaluation', response_data.get('evaluacion', '')),
            evidence_used=response_data.get('evidence_used', []),
            clinical_reasoning=response_data.get('clinical_reasoning', ''),
            response=response_data.get('response', response_data.get('respuesta', '')),
            recommendations=response_data.get('recommendations', response_data.get('recomendaciones', [])),
            evidence_level=response_data.get('evidence_level', 'Unknown'),
            confidence_level=response_data.get('confidence_level', 'medium'),
            information_limitations=response_data.get('information_limitations', []),
            requires_additional_info=response_data.get('requires_additional_info', False),
            additional_questions=response_data.get('additional_questions', []),
            sources=self.sources
        )
