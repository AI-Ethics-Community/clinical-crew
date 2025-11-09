"""
Cliente para búsqueda en PubMed/NCBI.
"""
import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from Bio import Entrez
import httpx

from app.config.settings import settings
from app.models.database import BusquedaPubMed
import google.generativeai as genai


class PubMedClient:
    """Cliente para interactuar con PubMed API"""

    def __init__(self):
        """Inicializa el cliente de PubMed"""
        # Configurar Entrez
        Entrez.email = settings.pubmed_email
        Entrez.tool = settings.pubmed_tool_name

        if settings.pubmed_api_key:
            Entrez.api_key = settings.pubmed_api_key

        self.max_results = settings.pubmed_max_results
        
        # Configure Gemini for keyword extraction
        genai.configure(api_key=settings.gemini_api_key)
        self.gemini_model = genai.GenerativeModel(
            model_name=settings.gemini_flash_model,  # Use Flash for speed
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1024
            )
        )

    async def extract_medical_keywords_async(
        self, 
        pregunta: str, 
        specialty: str
    ) -> Dict[str, Any]:
        """
        Extract key medical concepts from Spanish question and translate to English/MeSH terms.
        
        Args:
            pregunta: Spanish medical consultation question
            specialty: Medical specialty context
            
        Returns:
            Dict with 'keywords', 'mesh_terms', 'suggested_query'
            Falls back to {'keywords': [specialty]} if extraction fails
        """
        try:
            print(f"Extracting keywords from: {pregunta[:80]}...")
            
            # System instruction for Gemini
            system_instruction = """You are a medical terminology expert specialized in translating Spanish medical consultation questions into structured English medical terminology for PubMed searches.

Your task is to:
1. Analyze the Spanish medical question
2. Extract 3-5 core medical concepts (diagnoses, treatments, patient demographics, clinical context)
3. Translate each concept to standard English medical terminology
4. Suggest appropriate MeSH (Medical Subject Headings) terms when applicable
5. Create a concise search query combining the most relevant terms

Guidelines:
- Focus on specific medical conditions, not generic terms
- Include patient context (age, pregnancy, comorbidities) if mentioned
- Prioritize MeSH terms over free text when possible
- Keep queries focused (3-5 terms maximum)
- Use standard medical English (e.g., "arrhythmias, cardiac" not "heart rhythm problems")

Return ONLY a JSON object with this exact structure:
{
  "keywords": ["keyword1", "keyword2", ...],
  "mesh_terms": ["term1[mesh]", "term2[mesh]", ...],
  "suggested_query": "combined query string"
}"""
            
            # User prompt with question and specialty
            user_prompt = f"""Analyze this medical consultation question and extract keywords for a PubMed search.

Question: "{pregunta}"

Specialty context: {specialty}

Remember to:
- Extract 3-5 key medical concepts
- Translate to English medical terminology
- Suggest MeSH terms when applicable
- Return ONLY the JSON object, no additional text"""
            
            # Call Gemini
            model = genai.GenerativeModel(
                model_name=settings.gemini_flash_model,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=1024
                ),
                system_instruction=system_instruction
            )
            
            response = await model.generate_content_async(user_prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            else:
                json_str = response_text
            
            # Parse JSON
            keywords_data = json.loads(json_str)
            
            # Validate structure
            if not isinstance(keywords_data.get('keywords'), list) or not keywords_data['keywords']:
                raise ValueError("Invalid keywords structure")
            
            print(f"✓ Extracted {len(keywords_data['keywords'])} keywords: {keywords_data['keywords'][:3]}")
            return keywords_data
            
        except Exception as e:
            print(f"⚠ Keyword extraction failed: {str(e)}. Falling back to specialty search.")
            # Fallback to simple specialty search
            return {
                "keywords": [specialty],
                "mesh_terms": [],
                "suggested_query": specialty
            }

    def build_mesh_query(
        self,
        keywords_data: Dict[str, Any],
        min_year: Optional[int] = None,
        max_year: Optional[int] = None
    ) -> str:
        """
        Build a PubMed query from extracted keywords and MeSH terms.
        
        Args:
            keywords_data: Dict with 'keywords' and 'mesh_terms' from extraction
            min_year: Minimum publication year (default: from settings)
            max_year: Maximum publication year (default: from settings)
            
        Returns:
            Formatted E-utilities compatible query string
        """
        min_year = min_year or settings.pubmed_min_year
        max_year = max_year or settings.pubmed_max_year
        
        # Use MeSH terms if available, otherwise use keywords
        mesh_terms = keywords_data.get('mesh_terms', [])
        keywords = keywords_data.get('keywords', [])
        
        query_parts = []
        
        if mesh_terms:
            # Use MeSH terms (already formatted with [mesh] tag)
            query_parts = mesh_terms[:5]  # Limit to 5 terms
        elif keywords:
            # Use keywords as free text
            query_parts = [f"{kw}" for kw in keywords[:5]]
        else:
            # Fallback to empty query
            return ""
        
        # Combine with AND
        query = " AND ".join(query_parts)
        
        # Add date range filter
        date_filter = f'"{min_year}/01/01"[dp] : "{max_year}/12/31"[dp]'
        query = f"{query} AND {date_filter}"
        
        return query

    def search_with_retry(
        self,
        query: str,
        max_results: Optional[int] = None,
        sort: str = "relevance"
    ) -> List[str]:
        """
        Search PubMed with exponential backoff retry on failures.
        
        Args:
            query: Query string
            max_results: Maximum number of results
            sort: Sort order
            
        Returns:
            List of PMIDs (empty list if all retries fail)
        """
        max_results = max_results or self.max_results
        max_attempts = settings.pubmed_retry_max_attempts
        backoff_factor = settings.pubmed_retry_backoff_factor
        
        for attempt in range(max_attempts):
            try:
                print(f"PubMed search attempt {attempt + 1}/{max_attempts}: {query[:80]}...")
                
                handle = Entrez.esearch(
                    db="pubmed",
                    term=query,
                    retmax=max_results,
                    sort=sort
                )
                record = Entrez.read(handle)
                handle.close()
                
                pmids = record["IdList"]
                print(f"✓ Found {len(pmids)} articles")
                return pmids
                
            except Exception as e:
                error_msg = str(e)
                print(f"✗ PubMed search error: {error_msg}")
                
                # Check if it's a retryable error
                is_retryable = (
                    "Search Backend failed" in error_msg or
                    "Database is not supported" in error_msg or
                    "Couldn't resolve" in error_msg
                )
                
                if not is_retryable or attempt == max_attempts - 1:
                    # Non-retryable error or final attempt
                    print(f"⚠ Giving up after {attempt + 1} attempts")
                    return []
                
                # Calculate backoff time
                wait_time = backoff_factor ** attempt
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        return []

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        sort: str = "relevance"
    ) -> List[str]:
        """
        Busca artículos en PubMed.

        Args:
            query: Query de búsqueda
            max_results: Número máximo de resultados
            sort: Criterio de ordenamiento (relevance, pub_date)

        Returns:
            Lista de PMIDs
        """
        max_results = max_results or self.max_results

        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort=sort
            )
            record = Entrez.read(handle)
            handle.close()

            return record["IdList"]

        except Exception as e:
            print(f"Error en búsqueda PubMed: {str(e)}")
            return []

    def fetch_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Obtiene detalles de artículos por PMID con batch processing.

        Args:
            pmids: Lista de PMIDs

        Returns:
            Lista de artículos con detalles
        """
        if not pmids:
            return []

        articles = []
        batch_size = settings.pubmed_batch_size
        total_batches = (len(pmids) + batch_size - 1) // batch_size
        
        print(f"Fetching {len(pmids)} articles in {total_batches} batches...")
        
        for i in range(0, len(pmids), batch_size):
            batch_num = (i // batch_size) + 1
            batch_ids = pmids[i:i + batch_size]
            
            try:
                print(f"  Processing batch {batch_num}/{total_batches} ({len(batch_ids)} articles)...")
                
                # Convert list of PMIDs to string
                ids = ",".join(batch_ids)

                # Fetch summaries for this batch
                handle = Entrez.efetch(
                    db="pubmed",
                    id=ids,
                    rettype="xml",
                    retmode="xml"
                )

                records = Entrez.read(handle)
                handle.close()

                # Parse articles in this batch
                for article_data in records['PubmedArticle']:
                    article = self._parse_article(article_data)
                    articles.append(article)
                
                print(f"  ✓ Batch {batch_num}/{total_batches} completed")
                
                # Rate limit compliance: wait 0.5s between batches
                if i + batch_size < len(pmids):
                    time.sleep(0.5)

            except Exception as e:
                print(f"  ✗ Batch {batch_num}/{total_batches} failed: {str(e)}")
                # Continue with next batch instead of failing completely
                continue
        
        print(f"✓ Successfully fetched {len(articles)}/{len(pmids)} articles")
        return articles

    def _parse_article(self, article_data: Dict) -> Dict[str, Any]:
        """
        Parsea la información de un artículo.

        Args:
            article_data: Datos del artículo de Entrez

        Returns:
            Diccionario con información del artículo
        """
        medline_citation = article_data.get('MedlineCitation', {})
        article_info = medline_citation.get('Article', {})

        # PMID
        pmid = str(medline_citation.get('PMID', ''))

        # Título
        title = article_info.get('ArticleTitle', 'Sin título')

        # Abstract
        abstract_data = article_info.get('Abstract', {})
        abstract_texts = abstract_data.get('AbstractText', [])

        if isinstance(abstract_texts, list):
            abstract = " ".join([str(text) for text in abstract_texts])
        else:
            abstract = str(abstract_texts) if abstract_texts else ""

        # Autores
        author_list = article_info.get('AuthorList', [])
        authors = []
        for author in author_list[:5]:  # Primeros 5 autores
            last_name = author.get('LastName', '')
            fore_name = author.get('ForeName', '')
            if last_name:
                authors.append(f"{last_name} {fore_name}".strip())

        # Journal
        journal = article_info.get('Journal', {})
        journal_title = journal.get('Title', '')

        # Fecha de publicación
        pub_date = journal.get('JournalIssue', {}).get('PubDate', {})
        year = pub_date.get('Year', '')
        month = pub_date.get('Month', '')
        day = pub_date.get('Day', '')

        date_str = f"{year}-{month}-{day}" if year else ""

        # DOI
        article_ids = article_data.get('PubmedData', {}).get('ArticleIdList', [])
        doi = ""
        for article_id in article_ids:
            if article_id.attributes.get('IdType') == 'doi':
                doi = str(article_id)
                break

        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal_title,
            "publication_date": date_str,
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        }

    def search_and_fetch(
        self,
        query: str,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca y obtiene detalles de artículos en un solo paso.

        Args:
            query: Query de búsqueda
            max_results: Número máximo de resultados

        Returns:
            Lista de artículos con detalles completos
        """
        pmids = self.search(query, max_results)
        return self.fetch_details(pmids)

    async def search_with_cache(
        self,
        query: str,
        specialty: Optional[str] = None,
        max_results: Optional[int] = None,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Busca en PubMed con caché en MongoDB.

        Args:
            query: Query de búsqueda
            specialty: Especialidad relacionada
            max_results: Número máximo de resultados
            force_refresh: Forzar nueva búsqueda

        Returns:
            Lista de artículos
        """
        # Buscar en caché
        if not force_refresh:
            cached = await BusquedaPubMed.find_one(
                BusquedaPubMed.query == query
            )

            if cached and cached.es_valido():
                print(f"✓ Usando caché para: {query}")
                return cached.articulos

        # Realizar nueva búsqueda
        print(f"🔍 Buscando en PubMed: {query}")
        articulos = self.search_and_fetch(query, max_results)

        # Guardar en caché
        pmids = [art['pmid'] for art in articulos]

        cached_search = BusquedaPubMed(
            query=query,
            specialty=specialty,
            pmids=pmids,
            total_results=len(articulos),
            articulos=articulos
        )

        await cached_search.insert()

        return articulos

    def format_articles_for_context(self, articles: List[Dict[str, Any]]) -> str:
        """
        Formatea artículos para incluir en el contexto del LLM.

        Args:
            articles: Lista de artículos

        Returns:
            Texto formateado
        """
        if not articles:
            return "No se encontraron artículos relevantes en PubMed."

        formatted = []

        for i, article in enumerate(articles, 1):
            authors_str = ", ".join(article['authors'][:3])
            if len(article['authors']) > 3:
                authors_str += " et al."

            article_text = f"""
[Artículo {i}]
Título: {article['title']}
Autores: {authors_str}
Journal: {article['journal']}
Año: {article['publication_date']}
PMID: {article['pmid']}

Resumen:
{article['abstract'][:500]}...

URL: {article['url']}
""".strip()

            formatted.append(article_text)

        return "\n\n" + "\n\n---\n\n".join(formatted)

    def get_citation(self, article: Dict[str, Any]) -> str:
        """
        Genera una cita bibliográfica del artículo.

        Args:
            article: Diccionario con información del artículo

        Returns:
            Cita formateada
        """
        authors_str = ", ".join(article['authors'][:3])
        if len(article['authors']) > 3:
            authors_str += " et al."

        citation = f"{authors_str}. {article['title']}. {article['journal']}. {article['publication_date']}. PMID: {article['pmid']}"

        return citation


# Instancia global del cliente
pubmed_client = PubMedClient()
