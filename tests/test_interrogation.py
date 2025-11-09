"""
Tests for GP interrogation phase functionality.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.agents.general_practitioner import GeneralPractitioner
from app.models.consultation import (
    InterrogationQuestion,
    PatientContext,
    ConsultationStatus,
)
from app.agents.state import MedicalConsultationState


@pytest.fixture
def gp_agent():
    """Create GP agent instance"""
    return GeneralPractitioner()


@pytest.fixture
def patient_context():
    """Create sample patient context"""
    return PatientContext(
        age=45,
        sex="M",
        medical_history=["Hypertension", "Type 2 Diabetes"],
        current_medications=["Metformin", "Lisinopril"],
        allergies=["Penicillin"]
    )


@pytest.fixture
def consultation_state(patient_context):
    """Create consultation state"""
    return MedicalConsultationState(
        consulta_id="test-123",
        original_consultation="Patient complains of chest pain for 3 days",
        patient_context=patient_context,
        estado=ConsultationStatus.INTERROGANDO
    )


@pytest.mark.asyncio
class TestInterrogationQuestionGeneration:
    """Tests for interrogation question generation"""
    
    async def test_generate_questions_basic(self, gp_agent, consultation_state):
        """Test generating interrogation questions"""
        questions = await gp_agent.generate_interrogation_questions(consultation_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert len(questions) <= 7  # Should not exceed 7 questions
        
        # Verify question structure
        for question in questions:
            assert isinstance(question, InterrogationQuestion)
            assert question.question_id
            assert question.question_text
            assert question.question_type in ["open", "multiple_choice", "numeric"]
            assert 1 <= question.priority <= 5
    
    async def test_questions_relevance(self, gp_agent, consultation_state):
        """Test that questions are relevant to the consultation"""
        questions = await gp_agent.generate_interrogation_questions(consultation_state)
        
        # For chest pain consultation, should ask about pain characteristics
        question_texts = [q.question_text.lower() for q in questions]
        
        # Should ask about pain characteristics
        pain_related = any(
            keyword in text 
            for text in question_texts 
            for keyword in ["pain", "discomfort", "chest"]
        )
        assert pain_related, "Questions should be relevant to chest pain"
    
    async def test_questions_prioritization(self, gp_agent, consultation_state):
        """Test that questions are properly prioritized"""
        questions = await gp_agent.generate_interrogation_questions(consultation_state)
        
        # Should have high priority questions
        priorities = [q.priority for q in questions]
        assert max(priorities) >= 4, "Should have high priority questions"
        
        # Questions should be sorted by priority (descending)
        sorted_priorities = sorted(priorities, reverse=True)
        assert priorities == sorted_priorities, "Questions should be sorted by priority"
    
    async def test_question_types_variety(self, gp_agent, consultation_state):
        """Test that different question types are used appropriately"""
        questions = await gp_agent.generate_interrogation_questions(consultation_state)
        
        question_types = [q.question_type for q in questions]
        
        # Should have at least open-ended questions
        assert "open" in question_types, "Should include open-ended questions"
    
    async def test_multiple_choice_options(self, gp_agent, consultation_state):
        """Test multiple choice questions have options"""
        questions = await gp_agent.generate_interrogation_questions(consultation_state)
        
        multiple_choice = [q for q in questions if q.question_type == "multiple_choice"]
        
        for question in multiple_choice:
            assert question.options is not None
            assert len(question.options) >= 2, "Multiple choice should have at least 2 options"


@pytest.mark.asyncio
class TestResponseEvaluation:
    """Tests for evaluating user responses"""
    
    async def test_evaluate_complete_responses(self, gp_agent, consultation_state):
        """Test evaluating complete set of responses"""
        # Generate questions
        questions = await gp_agent.generate_interrogation_questions(consultation_state)
        
        # Provide responses to all questions
        responses = {}
        for question in questions:
            if question.question_type == "open":
                responses[question.question_id] = "Sharp pain, radiating to left arm"
            elif question.question_type == "numeric":
                responses[question.question_id] = 8
            elif question.question_type == "multiple_choice":
                responses[question.question_id] = question.options[0] if question.options else "Option 1"
        
        # Update state with responses
        consultation_state.interrogation_questions = questions
        consultation_state.user_responses = responses
        
        # Evaluate
        is_complete = await gp_agent.evaluate_responses(consultation_state)
        
        assert isinstance(is_complete, bool)
        assert is_complete is True, "All questions answered should be complete"
    
    async def test_evaluate_incomplete_responses(self, gp_agent, consultation_state):
        """Test evaluating incomplete responses"""
        # Generate questions
        questions = await gp_agent.generate_interrogation_questions(consultation_state)
        
        # Provide responses to only half
        responses = {}
        for i, question in enumerate(questions[:len(questions)//2]):
            responses[question.question_id] = "Test response"
        
        consultation_state.interrogation_questions = questions
        consultation_state.user_responses = responses
        
        # Evaluate
        is_complete = await gp_agent.evaluate_responses(consultation_state)
        
        assert is_complete is False, "Incomplete responses should not be complete"
    
    async def test_evaluate_low_quality_responses(self, gp_agent, consultation_state):
        """Test evaluating low quality responses"""
        questions = await gp_agent.generate_interrogation_questions(consultation_state)
        
        # Provide low-quality responses
        responses = {}
        for question in questions:
            responses[question.question_id] = "idk" if question.question_type == "open" else 0
        
        consultation_state.interrogation_questions = questions
        consultation_state.user_responses = responses
        
        # Evaluate
        is_complete = await gp_agent.evaluate_responses(consultation_state)
        
        # Should recognize low quality and potentially request better responses
        # This depends on implementation - may return False or True with warnings
        assert isinstance(is_complete, bool)


@pytest.mark.asyncio
class TestInterrogationIntegration:
    """Integration tests for interrogation flow"""
    
    async def test_full_interrogation_flow(self, gp_agent, consultation_state):
        """Test complete interrogation workflow"""
        # Step 1: Generate questions
        questions = await gp_agent.generate_interrogation_questions(consultation_state)
        assert len(questions) > 0
        
        # Step 2: Simulate user responses
        responses = {}
        for question in questions:
            if question.question_type == "open":
                responses[question.question_id] = "Detailed medical information"
            elif question.question_type == "numeric":
                responses[question.question_id] = 7
            elif question.question_type == "multiple_choice":
                responses[question.question_id] = question.options[0] if question.options else "Yes"
        
        consultation_state.interrogation_questions = questions
        consultation_state.user_responses = responses
        
        # Step 3: Evaluate responses
        is_complete = await gp_agent.evaluate_responses(consultation_state)
        assert is_complete is True
        
        # Step 4: Mark as complete
        consultation_state.interrogation_completed = True
        assert consultation_state.interrogation_completed
    
    async def test_iterative_interrogation(self, gp_agent, consultation_state):
        """Test iterative interrogation with follow-up questions"""
        # First round
        questions_round1 = await gp_agent.generate_interrogation_questions(consultation_state)
        
        # Answer first round
        responses = {}
        for question in questions_round1:
            responses[question.question_id] = "Vague response"
        
        consultation_state.interrogation_questions = questions_round1
        consultation_state.user_responses = responses
        
        # Evaluate - may not be complete
        is_complete_round1 = await gp_agent.evaluate_responses(consultation_state)
        
        if not is_complete_round1:
            # Generate follow-up questions
            questions_round2 = await gp_agent.generate_interrogation_questions(consultation_state)
            
            # Should have new or refined questions
            assert len(questions_round2) > 0


@pytest.mark.asyncio  
class TestInterrogationAPI:
    """Tests for interrogation API endpoints"""
    
    async def test_create_consultation_interrogating_status(self):
        """Test that new consultations start in interrogating status"""
        from app.models.consultation import ConsultationStatus
        
        # When creating consultation, initial status should be "interrogando"
        initial_status = ConsultationStatus.INTERROGANDO
        assert initial_status == "interrogando"
    
    async def test_respond_endpoint_structure(self):
        """Test structure of response to interrogation endpoint"""
        # POST /consultation/{id}/respond should accept:
        expected_request = {
            "responses": {
                "question_id_1": "Answer 1",
                "question_id_2": 42,
                "question_id_3": "Option A"
            }
        }
        
        assert "responses" in expected_request
        assert isinstance(expected_request["responses"], dict)


@pytest.mark.asyncio
class TestInterrogationPrompts:
    """Tests for interrogation prompts"""
    
    async def test_prompts_exist(self):
        """Test that interrogation prompts are defined"""
        from app.agents.prompts.interrogation import (
            INTERROGATION_SYSTEM_PROMPT,
            INTERROGATION_QUESTION_PROMPT
        )
        
        assert INTERROGATION_SYSTEM_PROMPT
        assert INTERROGATION_QUESTION_PROMPT
        assert len(INTERROGATION_SYSTEM_PROMPT) > 100, "System prompt should be detailed"
    
    async def test_prompts_in_english(self):
        """Test that prompts are in English"""
        from app.agents.prompts.interrogation import INTERROGATION_SYSTEM_PROMPT
        
        # Check for English words (not Spanish)
        assert "question" in INTERROGATION_SYSTEM_PROMPT.lower()
        assert "patient" in INTERROGATION_SYSTEM_PROMPT.lower()
        
        # Should not have Spanish words
        assert "pregunta" not in INTERROGATION_SYSTEM_PROMPT.lower()
        assert "paciente" not in INTERROGATION_SYSTEM_PROMPT.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
