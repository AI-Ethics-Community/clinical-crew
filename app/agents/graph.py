"""
LangGraph workflow for multi-agent medical consultation system.
"""
import asyncio
from typing import TypedDict, List, Dict, Any, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from app.agents.general_practitioner import general_practitioner
from app.agents.specialists import get_specialist_agent
from app.models.consultation import (
    EvaluacionGeneral,
    InterconsultationNote,
    CounterReferralNote,
    PatientContext,
    ClinicalRecord
)
from app.services.notes_service import notas_service
from app.models.database import MedicalConsultation


class MedicalConsultationState(TypedDict):
    """State for the medical consultation workflow"""

    # Input
    original_consultation: str
    patient_context: Dict[str, Any]
    consulta_id: str

    # GP evaluation
    general_evaluation: Dict[str, Any] | None

    # Interconsultations
    interconsultations: List[Dict[str, Any]]
    counter_referrals: List[Dict[str, Any]]

    # Additional information
    pending_questions: List[str]
    additional_information: Dict[str, Any] | None

    # Final output
    clinical_record: Dict[str, Any] | None
    final_response: str | None

    # Control flow
    estado: str  # evaluating, consulting, waiting_info, integrating, completed
    error: str | None


async def evaluate_initial_consultation(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: General practitioner evaluates the consultation.

    Args:
        state: Current workflow state

    Returns:
        Updated state with evaluation
    """
    print("🩺 GP: Evaluating consultation...")

    # Parse patient context
    contexto = PatientContext(**state['patient_context'])

    # Evaluate
    evaluacion = await general_practitioner.evaluate_consultation(
        consultation=state['original_consultation'],
        patient_context=contexto
    )

    # Update database
    consulta_db = await MedicalConsultation.get(state['consulta_id'])
    if consulta_db:
        consulta_db.general_evaluation = evaluacion
        consulta_db.add_trace("evaluate_consultation", {
            "can_answer_directly": evaluacion.can_answer_directly,
            "specialists": evaluacion.required_specialists
        })
        await consulta_db.save()

    # Update state
    state['general_evaluation'] = evaluacion.model_dump()

    if evaluacion.can_answer_directly:
        state['estado'] = 'completed'
        state['final_response'] = evaluacion.respuesta_directa
    else:
        state['estado'] = 'consulting'

    return state


async def generate_interconsultations(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: Generate interconsultation notes for specialists.

    Args:
        state: Current workflow state

    Returns:
        Updated state with interconsultations
    """
    print("📋 GP: Generating interconsultation notes...")

    evaluacion = EvaluacionGeneral(**state['general_evaluation'])
    contexto = PatientContext(**state['patient_context'])

    interconsultations = []

    for specialty in evaluacion.required_specialists:
        print(f"  → Generating note for {specialty}")

        interconsultation = await general_practitioner.generate_interconsulta(
            specialty=specialty,
            consultation=state['original_consultation'],
            patient_context=contexto
        )

        interconsultations.append(interconsultation.model_dump())

    # Update database
    consulta_db = await MedicalConsultation.get(state['consulta_id'])
    if consulta_db:
        for ic in interconsultations:
            consulta_db.agregar_interconsulta(InterconsultationNote(**ic))
        consulta_db.add_trace("generate_interconsultations", {
            "count": len(interconsultations)
        })
        await consulta_db.save()

    state['interconsultations'] = interconsultations

    return state


async def execute_specialists(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: Execute specialist agents in parallel.

    Args:
        state: Current workflow state

    Returns:
        Updated state with counter-referrals
    """
    print("🔬 Executing specialist consultations in parallel...")

    contexto = PatientContext(**state['patient_context'])

    # Execute all specialists in parallel
    async def process_interconsulta(interconsulta_data: Dict[str, Any]) -> Dict[str, Any]:
        interconsultation = InterconsultationNote(**interconsulta_data)

        print(f"  → {interconsultation.specialty}: Processing...")

        # Get specialist agent
        specialist = get_specialist_agent(interconsultation.specialty)

        # Process interconsultation
        counter_referral = await specialist.process_interconsulta(
            interconsulta_id=interconsultation.id,
            pregunta=interconsultation.specific_question,
            contexto=interconsultation.relevant_context,
            patient_context=contexto
        )

        print(f"  ✓ {interconsultation.specialty}: Response received")

        return counter_referral.model_dump()

    # Execute in parallel
    tasks = [process_interconsulta(ic) for ic in state['interconsultations']]
    counter_referrals = await asyncio.gather(*tasks)

    # Check if any specialist needs additional information
    preguntas = []
    for contra_data in counter_referrals:
        contra = CounterReferralNote(**contra_data)
        if contra.requires_additional_info:
            preguntas.extend(contra.additional_questions)

    # Update database
    consulta_db = await MedicalConsultation.get(state['consulta_id'])
    if consulta_db:
        for contra_data in counter_referrals:
            consulta_db.agregar_contrarreferencia(CounterReferralNote(**contra_data))

        if preguntas:
            consulta_db.pending_questions = preguntas
            consulta_db.actualizar_estado('esperando_info')

        consulta_db.add_trace("execute_specialists", {
            "count": len(counter_referrals),
            "requires_additional_info": len(preguntas) > 0
        })
        await consulta_db.save()

    state['counter_referrals'] = counter_referrals
    state['pending_questions'] = preguntas

    if preguntas:
        state['estado'] = 'waiting_info'
    else:
        state['estado'] = 'integrating'

    return state


async def integrate_responses(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: Integrate specialist responses into final answer.

    Args:
        state: Current workflow state

    Returns:
        Updated state with integrated response
    """
    print("🔄 GP: Integrating specialist responses...")

    contexto = PatientContext(**state['patient_context'])
    counter_referrals = [CounterReferralNote(**c) for c in state['counter_referrals']]

    # Integrate
    response_data = await general_practitioner.integrate_responses(
        consultation=state['original_consultation'],
        patient_context=contexto,
        counter_referrals=counter_referrals
    )

    # Generate complete clinical record
    interconsultations = [InterconsultationNote(**ic) for ic in state['interconsultations']]

    expediente_text = notas_service.generar_expediente_completo(
        original_consultation=state['original_consultation'],
        patient_context=contexto,
        nota_medico_general=response_data.get('general_summary', ''),
        interconsultations=interconsultations,
        counter_referrals=counter_referrals,
        final_response=response_data.get('final_response', ''),
        management_plan=response_data.get('management_plan'),
        seguimiento=response_data.get('recommended_followup')
    )

    # Create clinical_record object
    clinical_record = ClinicalRecord(
        general_summary=response_data.get('general_summary', ''),
        complete_notes=expediente_text,
        final_response=response_data.get('final_response', ''),
        management_plan=response_data.get('management_plan'),
        recommended_followup=response_data.get('recommended_followup')
    )

    # Update database
    consulta_db = await MedicalConsultation.get(state['consulta_id'])
    if consulta_db:
        consulta_db.clinical_record = clinical_record
        consulta_db.actualizar_estado('completado')
        consulta_db.add_trace("integrate_responses", {
            "expediente_generated": True
        })
        await consulta_db.save()

    state['clinical_record'] = clinical_record.model_dump()
    state['final_response'] = response_data.get('final_response', '')
    state['estado'] = 'completed'

    print("✓ Integration complete!")

    return state


def should_consult_specialists(state: MedicalConsultationState) -> str:
    """
    Router: Decide if we need to consult specialists.

    Args:
        state: Current workflow state

    Returns:
        Next node name
    """
    if state['general_evaluation']['can_answer_directly']:
        return "end"
    else:
        return "generate_interconsultations"


def should_wait_for_info(state: MedicalConsultationState) -> str:
    """
    Router: Decide if we need to wait for additional information.

    Args:
        state: Current workflow state

    Returns:
        Next node name
    """
    if state['pending_questions']:
        return "wait_for_info"
    else:
        return "integrate"


def create_workflow() -> StateGraph:
    """
    Create the medical consultation workflow graph.

    Returns:
        Compiled workflow
    """
    # Create graph
    workflow = StateGraph(MedicalConsultationState)

    # Add nodes
    workflow.add_node("evaluate", evaluate_initial_consultation)
    workflow.add_node("generate_interconsultations", generate_interconsultations)
    workflow.add_node("execute_specialists", execute_specialists)
    workflow.add_node("integrate", integrate_responses)

    # Set entry point
    workflow.set_entry_point("evaluate")

    # Add edges
    workflow.add_conditional_edges(
        "evaluate",
        should_consult_specialists,
        {
            "generate_interconsultations": "generate_interconsultations",
            "end": END
        }
    )

    workflow.add_edge("generate_interconsultations", "execute_specialists")

    workflow.add_conditional_edges(
        "execute_specialists",
        should_wait_for_info,
        {
            "integrate": "integrate",
            "wait_for_info": END  # Will be handled by API
        }
    )

    workflow.add_edge("integrate", END)

    # Compile
    app = workflow.compile()

    return app


# Global workflow instance
medical_consultation_workflow = create_workflow()
