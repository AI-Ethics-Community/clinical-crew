"""
General practitioner agent - coordinates the multi-agent workflow.
"""

import json
import uuid
from typing import Dict, Any, List, Optional

from app.services.gemini_client import gemini_medico_general
from app.agents.prompts.general_practitioner import (
    PROMPT_EVALUACION_INICIAL,
    PROMPT_GENERAR_INTERCONSULTA,
    PROMPT_INTEGRAR_RESPUESTAS,
    PROMPT_SOLICITAR_INFORMACION,
)
from app.agents.prompts.interrogation import (
    PROMPT_GENERATE_INTERROGATION_QUESTIONS,
    PROMPT_EVALUATE_RESPONSES,
)
from app.models.consultation import (
    GeneralEvaluation,
    InterconsultationNote,
    CounterReferralNote,
    PatientContext,
    InterrogationQuestion,
)
from app.models.notes import FormatoContextoPaciente


class GeneralPractitionerAgent:
    """
    General practitioner agent that coordinates the medical consultation workflow.

    Responsibilities:
    - Evaluate initial consultation
    - Decide whether to answer directly or consult specialists
    - Generate interconsultation notes
    - Integrate specialist responses
    - Generate final clinical report
    """

    def __init__(self):
        """Initialize general practitioner agent"""
        self.gemini_client = gemini_medico_general

    async def evaluate_consultation(
        self, consultation: str, patient_context: PatientContext
    ) -> GeneralEvaluation:
        """
        Evaluate initial consultation and decide on routing.

        Args:
            consultation: User's medical question
            patient_context: Patient context

        Returns:
            Evaluation with routing decision
        """
        # Format patient context
        contexto_str = FormatoContextoPaciente.formatear(patient_context.model_dump())

        # Build prompt
        prompt = PROMPT_EVALUACION_INICIAL.format(
            consultation=consultation, patient_context=contexto_str
        )

        # Generate evaluation
        response_text = await self.gemini_client.generate_content_async(prompt)

        # Parse response
        response_data = self._parse_json_response(response_text)

        # Create evaluation object
        evaluacion = GeneralEvaluation(
            can_answer_directly=response_data.get("can_answer_directly", False),
            required_specialists=response_data.get("required_specialists", []),
            reasoning=response_data.get("reasoning", response_data.get("razonamiento", "")),
            estimated_complexity=response_data.get("estimated_complexity", 0.5),
        )

        return evaluacion

    async def generate_interconsulta(
        self, specialty: str, consultation: str, patient_context: PatientContext
    ) -> InterconsultationNote:
        """
        Generate interconsultation note for a specialist.

        Args:
            specialty: Specialty to consult
            consultation: Original consultation
            patient_context: Patient context

        Returns:
            Interconsultation note
        """
        # Format patient context
        contexto_str = FormatoContextoPaciente.formatear(patient_context.model_dump())

        # Build prompt
        prompt = PROMPT_GENERAR_INTERCONSULTA.format(
            specialty=specialty, consultation=consultation, patient_context=contexto_str
        )

        # Generate interconsultation
        response_text = await self.gemini_client.generate_content_async(prompt)

        # Parse response
        response_data = self._parse_json_response(response_text)

        # Create interconsultation note
        interconsultation = InterconsultationNote(
            id=str(uuid.uuid4()),
            specialty=specialty,
            specific_question=response_data.get("specific_question", ""),
            relevant_context=response_data.get("relevant_context", {}),
        )

        return interconsultation

    async def integrate_responses(
        self,
        consultation: str,
        patient_context: PatientContext,
        counter_referrals: List[CounterReferralNote],
    ) -> Dict[str, Any]:
        """
        Integrate specialist responses into final answer.

        Args:
            consultation: Original consultation
            patient_context: Patient context
            counter_referrals: Specialist responses

        Returns:
            Integrated response with final answer and management plan
        """
        # Format patient context
        contexto_str = FormatoContextoPaciente.formatear(patient_context.model_dump())

        # Format counter-referrals
        contrarreferencias_str = self._format_contrarreferencias(counter_referrals)

        # Build prompt
        prompt = PROMPT_INTEGRAR_RESPUESTAS.format(
            consultation=consultation,
            patient_context=contexto_str,
            counter_referrals=contrarreferencias_str,
        )

        # Generate integration
        response_text = await self.gemini_client.generate_content_async(prompt)

        # Parse response
        response_data = self._parse_json_response(response_text)

        return response_data

    async def request_additional_information(
        self, preguntas: List[str]
    ) -> Dict[str, Any]:
        """
        Format requests for additional information from user.

        Args:
            preguntas: Questions that need answers

        Returns:
            Formatted request for user
        """
        # Format questions
        preguntas_str = "\n".join([f"- {p}" for p in preguntas])

        # Build prompt
        prompt = PROMPT_SOLICITAR_INFORMACION.format(preguntas=preguntas_str)

        # Generate request
        response_text = await self.gemini_client.generate_content_async(prompt)

        # Parse response
        response_data = self._parse_json_response(response_text)

        return response_data

    async def generate_interrogation_questions(
        self, consultation: str, patient_context: PatientContext
    ) -> Dict[str, Any]:
        """
        Generate interrogation questions for patient information gathering.

        Args:
            consultation: Medical consultation question
            patient_context: Patient context

        Returns:
            Dictionary with questions, can_proceed flag, and reasoning
        """
        contexto_str = FormatoContextoPaciente.formatear(patient_context.model_dump())

        prompt = PROMPT_GENERATE_INTERROGATION_QUESTIONS.format(
            consultation=consultation, patient_context=contexto_str
        )

        response_text = await self.gemini_client.generate_content_async(prompt)
        response_data = self._parse_json_response(response_text)

        # Validate that multiple_choice questions have options
        if "questions" in response_data:
            for question in response_data["questions"]:
                if question.get("question_type") == "multiple_choice":
                    if not question.get("options") or len(question.get("options", [])) < 2:
                        print(f"WARNING: multiple_choice question '{question.get('question_id')}' missing valid options. "
                              f"Converting to 'open' type.")
                        question["question_type"] = "open"
                        question.pop("options", None)

        return response_data

    async def evaluate_responses(
        self, questions: List[InterrogationQuestion], responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate if user responses are sufficient to proceed.

        Args:
            questions: Questions that were asked
            responses: User's responses

        Returns:
            Dictionary with is_sufficient, missing_critical_info, can_proceed, additional_questions
        """
        questions_str = json.dumps([q.model_dump() for q in questions], indent=2)
        responses_str = json.dumps(responses, indent=2)

        prompt = PROMPT_EVALUATE_RESPONSES.format(
            questions=questions_str, responses=responses_str
        )

        response_text = await self.gemini_client.generate_content_async(prompt)
        response_data = self._parse_json_response(response_text)

        return response_data

    def _format_contrarreferencias(
        self, counter_referrals: List[CounterReferralNote]
    ) -> str:
        """
        Format counter-referrals for integration prompt.

        Args:
            counter_referrals: List of counter-referrals

        Returns:
            Formatted text
        """
        formatted = []

        for i, contra in enumerate(counter_referrals, 1):
            text = f"""
[Specialist {i}: {contra.specialty}]

Evaluation:
{contra.evaluation}

Clinical Reasoning:
{contra.clinical_reasoning}

Response:
{contra.response}

Recommendations:
{self._format_list(contra.recommendations)}

Evidence Used:
{self._format_list(contra.evidence_used)}

Evidence Level: {contra.evidence_level}
""".strip()

            formatted.append(text)

        return "\n\n" + "\n\n---\n\n".join(formatted)

    def _format_list(self, items: List[str]) -> str:
        """Format list items with bullets."""
        if not items:
            return "None"
        return "\n".join([f"- {item}" for item in items])

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

            # Fallback: return empty dict
            return {}


# Global instance
general_practitioner = GeneralPractitionerAgent()
