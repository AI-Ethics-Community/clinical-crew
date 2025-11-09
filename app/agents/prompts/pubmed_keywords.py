"""
Prompts for PubMed keyword extraction.

This module contains prompts to extract medical keywords from Spanish medical
consultation questions and translate them to English MeSH terms for PubMed searches.
"""


def get_prompt_extract_pubmed_keywords() -> str:
    """
    Get system prompt for extracting medical keywords from Spanish questions.
    
    Returns:
        System instruction for Gemini to extract keywords and MeSH terms
    """
    return """You are a medical terminology expert specialized in translating Spanish medical consultation questions into structured English medical terminology for PubMed searches.

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
}

Example:
Input: "Solicito valoración de manejo de diabetes gestacional en paciente de 28 semanas con mal control glucémico"
Output:
{
  "keywords": ["gestational diabetes", "pregnancy", "third trimester", "glycemic control", "management"],
  "mesh_terms": ["diabetes, gestational[mesh]", "pregnancy trimester, third[mesh]", "blood glucose[mesh]"],
  "suggested_query": "diabetes, gestational[mesh] AND pregnancy trimester, third[mesh] AND blood glucose[mesh] AND therapy"
}
"""


def get_prompt_extract_keywords_user(pregunta: str, specialty: str) -> str:
    """
    Get user prompt with the specific question to analyze.
    
    Args:
        pregunta: Spanish medical consultation question
        specialty: Medical specialty context (e.g., cardiology, endocrinology)
        
    Returns:
        Formatted user prompt with question and specialty
    """
    return f"""Analyze this medical consultation question and extract keywords for a PubMed search.

Question: "{pregunta}"

Specialty context: {specialty}

Remember to:
- Extract 3-5 key medical concepts
- Translate to English medical terminology
- Suggest MeSH terms when applicable
- Return ONLY the JSON object, no additional text
"""
