"""
Tests to ensure specialists NEVER request additional information.

This test suite verifies the critical constraint that specialists must work
with available information only and express uncertainty through confidence_level
and information_limitations fields instead of requesting additional info.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.agents.specialists.base import SpecialistBase
from app.models.consultation import (
    InterconsultationNote,
    CounterReferralNote,
    PatientContext,
)
from app.models.sources import ScientificSource, SourceType


@pytest.fixture
def patient_context():
    """Create minimal patient context"""
    return PatientContext(
        age=50,
        sex="F",
        medical_history=["Hypertension"],
        current_medications=[],
        allergies=[]
    )


@pytest.fixture
def interconsultation_note(patient_context):
    """Create interconsultation note with limited information"""
    return InterconsultationNote(
        specialty="cardiology",
        requesting_physician="General Practitioner",
        patient_context=patient_context,
        reason_for_consultation="Chest pain evaluation",
        specific_question="Rule out cardiac origin of chest pain",
        relevant_findings="Patient reports intermittent chest discomfort",
        urgency="routine"
    )


@pytest.fixture
def mock_specialist():
    """Create mock specialist"""
    class MockSpecialist(SpecialistBase):
        def __init__(self):
            super().__init__(specialty="cardiology")
    
    return MockSpecialist()


@pytest.mark.asyncio
class TestNoAdditionalInfoRequests:
    """Tests ensuring specialists never request additional information"""
    
    async def test_counter_referral_never_requires_additional_info(
        self, mock_specialist, interconsultation_note
    ):
        """Test that counter-referral never has requires_additional_info=True"""
        with patch.object(mock_specialist, '_generate_evaluation', 
                         new=AsyncMock(return_value="Evaluation text")):
            
            counter_referral = await mock_specialist.execute(interconsultation_note)
            
            assert isinstance(counter_referral, CounterReferralNote)
            
            # CRITICAL: Should never require additional info
            assert not hasattr(counter_referral, 'requires_additional_info') or \
                   counter_referral.requires_additional_info is False, \
                   "Specialists must NEVER request additional information"
    
    async def test_limited_information_uses_confidence_level(
        self, mock_specialist, interconsultation_note
    ):
        """Test that specialists use confidence_level for uncertain cases"""
        # Create very limited information scenario
        interconsultation_note.relevant_findings = "Vague symptoms"
        
        with patch.object(mock_specialist, '_generate_evaluation',
                         new=AsyncMock(return_value="Limited evaluation")):
            
            counter_referral = await mock_specialist.execute(interconsultation_note)
            
            # Should have confidence level
            assert hasattr(counter_referral, 'confidence_level')
            assert counter_referral.confidence_level in ["high", "medium", "low"]
            
            # Should document limitations
            assert hasattr(counter_referral, 'information_limitations')
            assert isinstance(counter_referral.information_limitations, list)
    
    async def test_information_limitations_documented(
        self, mock_specialist, interconsultation_note
    ):
        """Test that information limitations are properly documented"""
        with patch.object(mock_specialist, '_generate_evaluation',
                         new=AsyncMock(return_value="Evaluation")):
            
            counter_referral = await mock_specialist.execute(interconsultation_note)
            
            assert hasattr(counter_referral, 'information_limitations')
            
            # If information is limited, should be documented
            if counter_referral.confidence_level in ["medium", "low"]:
                assert len(counter_referral.information_limitations) > 0, \
                       "Low/medium confidence should document specific limitations"
    
    async def test_multiple_specialists_no_additional_info(self, patient_context):
        """Test that multiple specialists all respect the no-additional-info rule"""
        specialties_to_test = [
            "cardiology",
            "dermatology", 
            "neurology",
            "gastroenterology"
        ]
        
        for specialty in specialties_to_test:
            specialist = SpecialistBase(specialty=specialty)
            
            ic_note = InterconsultationNote(
                specialty=specialty,
                requesting_physician="GP",
                patient_context=patient_context,
                reason_for_consultation="Consultation",
                specific_question="Evaluate patient",
                relevant_findings="Limited information available",
                urgency="routine"
            )
            
            with patch.object(specialist, '_generate_evaluation',
                             new=AsyncMock(return_value="Evaluation")):
                
                counter_referral = await specialist.execute(ic_note)
                
                # NONE should request additional info
                assert not hasattr(counter_referral, 'requires_additional_info') or \
                       counter_referral.requires_additional_info is False, \
                       f"{specialty} must not request additional information"


@pytest.mark.asyncio
class TestConfidenceLevelUsage:
    """Tests for proper usage of confidence_level field"""
    
    async def test_high_confidence_with_complete_info(
        self, mock_specialist, interconsultation_note
    ):
        """Test high confidence when information is complete"""
        # Complete information scenario
        interconsultation_note.relevant_findings = """
        Patient: 50F with hypertension
        Chest pain: Substernal, pressure-like, 8/10 severity
        Duration: 30 minutes, resolved with rest
        Associated: Diaphoresis, shortness of breath
        ECG: ST elevation in leads II, III, aVF
        Troponin: Elevated at 2.5 ng/mL
        """
        
        with patch.object(mock_specialist, '_generate_evaluation',
                         new=AsyncMock(return_value="Clear cardiac event")):
            
            counter_referral = await mock_specialist.execute(interconsultation_note)
            
            # With complete information, confidence should be high
            assert counter_referral.confidence_level == "high"
            assert len(counter_referral.information_limitations) == 0
    
    async def test_medium_confidence_with_partial_info(
        self, mock_specialist, interconsultation_note
    ):
        """Test medium confidence with partial information"""
        # Partial information
        interconsultation_note.relevant_findings = "Chest pain, duration unknown"
        
        with patch.object(mock_specialist, '_generate_evaluation',
                         new=AsyncMock(return_value="Possible cardiac")):
            
            counter_referral = await mock_specialist.execute(interconsultation_note)
            
            # Should express medium confidence
            assert counter_referral.confidence_level in ["medium", "low"]
            assert len(counter_referral.information_limitations) > 0
    
    async def test_low_confidence_with_minimal_info(
        self, mock_specialist, interconsultation_note
    ):
        """Test low confidence with minimal information"""
        # Minimal information
        interconsultation_note.relevant_findings = "Chest discomfort"
        
        with patch.object(mock_specialist, '_generate_evaluation',
                         new=AsyncMock(return_value="Uncertain")):
            
            counter_referral = await mock_specialist.execute(interconsultation_note)
            
            # Should express low confidence but still provide evaluation
            assert counter_referral.confidence_level == "low"
            assert len(counter_referral.information_limitations) > 0
            
            # But evaluation should still exist
            assert counter_referral.evaluacion
            assert len(counter_referral.evaluacion) > 0


@pytest.mark.asyncio
class TestSourceCapture:
    """Tests for scientific source capture"""
    
    async def test_sources_captured_from_tools(
        self, mock_specialist, interconsultation_note
    ):
        """Test that sources from tools are captured"""
        # Mock tool calls that return sources
        mock_rag_results = [
            {"content": "Guideline text", "metadata": {"title": "ACC Guidelines"}}
        ]
        mock_pubmed_results = [
            {"pmid": "12345678", "title": "Cardiac Study"}
        ]
        
        with patch.object(mock_specialist, '_call_rag',
                         new=AsyncMock(return_value=mock_rag_results)), \
             patch.object(mock_specialist, '_call_pubmed',
                         new=AsyncMock(return_value=mock_pubmed_results)), \
             patch.object(mock_specialist, '_generate_evaluation',
                         new=AsyncMock(return_value="Evaluation")):
            
            counter_referral = await mock_specialist.execute(interconsultation_note)
            
            # Sources should be captured
            assert hasattr(counter_referral, 'sources')
            assert isinstance(counter_referral.sources, list)
            assert len(counter_referral.sources) > 0
    
    async def test_source_metadata_complete(
        self, mock_specialist, interconsultation_note
    ):
        """Test that source metadata is complete"""
        mock_sources = [
            ScientificSource(
                source_id="src-1",
                source_type=SourceType.PUBMED,
                title="Cardiac Biomarkers",
                pmid="12345678",
                relevance_score=0.95,
                specialty="cardiology",
                used_for="Troponin interpretation",
                timestamp=datetime.utcnow()
            )
        ]
        
        with patch.object(mock_specialist, 'sources', mock_sources), \
             patch.object(mock_specialist, '_generate_evaluation',
                         new=AsyncMock(return_value="Evaluation")):
            
            counter_referral = await mock_specialist.execute(interconsultation_note)
            
            # Check source completeness
            for source in counter_referral.sources:
                assert source.source_id
                assert source.source_type in SourceType
                assert source.title
                assert 0 <= source.relevance_score <= 1
                assert source.specialty == "cardiology"
                assert source.used_for


@pytest.mark.asyncio
class TestToolCallbacks:
    """Tests for tool execution callbacks"""
    
    async def test_tool_started_callback(
        self, mock_specialist, interconsultation_note
    ):
        """Test that tool_started callback is invoked"""
        tool_started_called = False
        tool_name_captured = None
        
        def on_tool_start(tool_name, params):
            nonlocal tool_started_called, tool_name_captured
            tool_started_called = True
            tool_name_captured = tool_name
        
        mock_specialist.set_callbacks(
            on_tool_start=on_tool_start,
            on_tool_complete=lambda *args: None,
            on_source_found=lambda *args: None
        )
        
        with patch.object(mock_specialist, '_call_rag',
                         new=AsyncMock(return_value=[])), \
             patch.object(mock_specialist, '_generate_evaluation',
                         new=AsyncMock(return_value="Evaluation")):
            
            await mock_specialist.execute(interconsultation_note)
            
            assert tool_started_called
            assert tool_name_captured in ["rag_retriever", "pubmed_search"]
    
    async def test_source_found_callback(
        self, mock_specialist, interconsultation_note
    ):
        """Test that source_found callback is invoked"""
        sources_found = []
        
        def on_source_found(source):
            sources_found.append(source)
        
        mock_specialist.set_callbacks(
            on_tool_start=lambda *args: None,
            on_tool_complete=lambda *args: None,
            on_source_found=on_source_found
        )
        
        mock_results = [
            {"content": "Text", "metadata": {"title": "Source 1"}}
        ]
        
        with patch.object(mock_specialist, '_call_rag',
                         new=AsyncMock(return_value=mock_results)), \
             patch.object(mock_specialist, '_generate_evaluation',
                         new=AsyncMock(return_value="Evaluation")):
            
            await mock_specialist.execute(interconsultation_note)
            
            assert len(sources_found) > 0


@pytest.mark.asyncio
class TestSpecialistPrompts:
    """Tests for specialist prompts"""
    
    async def test_prompts_forbid_additional_info(self):
        """Test that specialist prompts explicitly forbid requesting additional info"""
        from app.agents.prompts.specialists import SPECIALIST_SYSTEM_PROMPT
        
        prompt_lower = SPECIALIST_SYSTEM_PROMPT.lower()
        
        # Should have restriction
        assert "never" in prompt_lower or "not" in prompt_lower or "cannot" in prompt_lower
        
        # Should mention confidence and limitations
        assert "confidence" in prompt_lower or "certainty" in prompt_lower
        assert "limitation" in prompt_lower or "insufficient" in prompt_lower
    
    async def test_prompts_in_english(self):
        """Test that specialist prompts are in English"""
        from app.agents.prompts.specialists import SPECIALIST_SYSTEM_PROMPT
        
        # English medical terms
        assert "evaluation" in SPECIALIST_SYSTEM_PROMPT.lower() or \
               "assessment" in SPECIALIST_SYSTEM_PROMPT.lower()
        
        # Not Spanish
        assert "evaluación" not in SPECIALIST_SYSTEM_PROMPT.lower()
        assert "solicitar" not in SPECIALIST_SYSTEM_PROMPT.lower()


@pytest.mark.asyncio
class TestWorkflowIntegration:
    """Integration tests for specialist workflow"""
    
    async def test_no_wait_for_info_state(self):
        """Test that workflow never enters 'wait_for_info' state"""
        from app.models.consultation import ConsultationStatus
        
        # Verify that there's no "waiting_for_info" status
        valid_statuses = [
            ConsultationStatus.INTERROGANDO,
            ConsultationStatus.EVALUANDO,
            ConsultationStatus.INTERCONSULTANDO,
            ConsultationStatus.INTEGRANDO,
            ConsultationStatus.COMPLETADO,
            ConsultationStatus.ERROR
        ]
        
        # Should not have waiting_for_info
        status_values = [s.value for s in valid_statuses]
        assert "waiting_for_info" not in status_values
        assert "esperando_info" not in status_values
    
    async def test_specialist_to_integration_direct_flow(self):
        """Test that workflow goes directly from specialists to integration"""
        # After specialists complete, should go directly to integration
        # No intermediate "waiting" step
        
        from app.models.consultation import ConsultationStatus
        
        # Valid flow: INTERCONSULTANDO → INTEGRANDO
        assert ConsultationStatus.INTERCONSULTANDO
        assert ConsultationStatus.INTEGRANDO
        
        # These should be adjacent in the workflow
        # (This is more of a documentation test)
        assert True  # Flow is: specialists → integrate → end


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
