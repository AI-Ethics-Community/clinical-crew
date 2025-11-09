"""
Test script for PubMed keyword extraction with problematic Spanish queries.
"""
import asyncio
from app.services.pubmed_client import pubmed_client
from app.config.settings import settings


async def test_keyword_extraction():
    """Test keyword extraction with the problematic Spanish query"""
    
    print("=" * 80)
    print("PubMed Keyword Extraction Test")
    print("=" * 80)
    print()
    
    # Test cases from the actual error
    test_cases = [
        {
            "pregunta": "Solicito su valoración para determinar el abordaje diagnóstico y terapéutico más seguro para la arritmia de la paciente, considerando su embarazo de 20 SDG.",
            "specialty": "cardiology"
        },
        {
            "pregunta": "Solicito valoración de opciones terapéuticas antiarrítmicas con el mejor perfil de seguridad fetal para paciente cursando el segundo trimestre de embarazo.",
            "specialty": "pharmacology"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"  Pregunta: {test_case['pregunta'][:80]}...")
        print(f"  Specialty: {test_case['specialty']}")
        print()
        
        # Step 1: Extract keywords
        print("Step 1: Extracting medical keywords...")
        keywords_data = await pubmed_client.extract_medical_keywords_async(
            test_case['pregunta'],
            test_case['specialty']
        )
        
        print(f"  Keywords: {keywords_data.get('keywords', [])}")
        print(f"  MeSH terms: {keywords_data.get('mesh_terms', [])}")
        print()
        
        # Step 2: Build query
        print("Step 2: Building PubMed query...")
        query = pubmed_client.build_mesh_query(
            keywords_data,
            min_year=settings.pubmed_min_year,
            max_year=settings.pubmed_max_year
        )
        
        print(f"  Final query: {query}")
        print()
        
        # Step 3: Search with retry (limit to 3 results for testing)
        print("Step 3: Searching PubMed with retry logic...")
        pmids = pubmed_client.search_with_retry(query, max_results=3)
        
        print(f"  Found {len(pmids)} articles: {pmids}")
        print()
        
        # Step 4: Fetch details (if we found anything)
        if pmids:
            print("Step 4: Fetching article details...")
            articles = pubmed_client.fetch_details(pmids)
            
            print(f"  Retrieved {len(articles)} articles")
            if articles:
                print(f"  First article: {articles[0]['title'][:80]}...")
                print(f"  PMID: {articles[0]['pmid']}")
                print(f"  URL: {articles[0]['url']}")
        else:
            print("Step 4: Skipped (no articles found)")
        
        print()
        print("-" * 80)
    
    print("\n✓ All tests completed!")
    print("\nExpected outcomes:")
    print("1. Keywords should be extracted in English")
    print("2. MeSH terms should have [mesh] tags")
    print("3. Query should NOT cause 'Search Backend failed' error")
    print("4. Should find relevant articles about pregnancy + arrhythmia")


if __name__ == "__main__":
    asyncio.run(test_keyword_extraction())
