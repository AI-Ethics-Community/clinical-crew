"""
Modelos para fuentes científicas utilizadas en consultas.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Tipos de fuentes científicas"""
    PUBMED = "pubmed"
    RAG_GUIDELINE = "rag_guideline"
    RAG_TEXTBOOK = "rag_textbook"
    CLINICAL_TRIAL = "clinical_trial"


class ScientificSource(BaseModel):
    """Fuente científica utilizada en una evaluación"""
    source_id: str = Field(..., description="ID único de la fuente")
    source_type: SourceType = Field(..., description="Tipo de fuente")
    title: str = Field(..., description="Título del documento/artículo")
    url: Optional[str] = Field(None, description="URL de la fuente")
    pmid: Optional[str] = Field(None, description="PubMed ID")
    doi: Optional[str] = Field(None, description="DOI")
    authors: Optional[List[str]] = Field(default_factory=list, description="Autores")
    publication_year: Optional[int] = Field(None, description="Año de publicación")
    abstract: Optional[str] = Field(None, description="Abstract/resumen")
    relevance_score: float = Field(..., description="Puntuación de relevancia (0-1)", ge=0.0, le=1.0)
    specialty: str = Field(..., description="Especialidad que utilizó la fuente")
    used_for: str = Field(..., description="Descripción de cómo se utilizó")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_id": "pmid_12345678",
                "source_type": "pubmed",
                "title": "Management of Type 2 Diabetes: ADA Guidelines 2024",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                "pmid": "12345678",
                "doi": "10.2337/dc24-S009",
                "authors": ["Smith J", "Johnson A"],
                "publication_year": 2024,
                "abstract": "Current guidelines for diabetes management...",
                "relevance_score": 0.95,
                "specialty": "endocrinology",
                "used_for": "Evaluar control glicémico y ajuste de medicación",
                "timestamp": "2024-11-09T01:00:00Z"
            }
        }
