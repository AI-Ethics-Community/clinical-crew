"""
Cliente para búsqueda en PubMed/NCBI.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from Bio import Entrez
import httpx

from app.config.settings import settings
from app.models.database import BusquedaPubMed


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
        Obtiene detalles de artículos por PMID.

        Args:
            pmids: Lista de PMIDs

        Returns:
            Lista de artículos con detalles
        """
        if not pmids:
            return []

        try:
            # Convertir lista de PMIDs a string
            ids = ",".join(pmids)

            # Fetch summaries
            handle = Entrez.efetch(
                db="pubmed",
                id=ids,
                rettype="xml",
                retmode="xml"
            )

            records = Entrez.read(handle)
            handle.close()

            articles = []

            for article_data in records['PubmedArticle']:
                article = self._parse_article(article_data)
                articles.append(article)

            return articles

        except Exception as e:
            print(f"Error obteniendo detalles: {str(e)}")
            return []

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
