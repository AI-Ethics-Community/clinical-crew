"""
LangGraph workflow for multi-agent medical consultation system with event streaming.
"""
import asyncio
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from app.agents.general_practitioner import general_practitioner
from app.agents.specialists import get_specialist_agent
from app.models.consultation import (
    GeneralEvaluation,
    InterconsultationNote,
    CounterReferralNote,
    PatientContext,
    ClinicalRecord,
    InterrogationQuestion
)
from app.services.notes_service import notas_service
from app.models.database import MedicalConsultation
from app.core.event_emitter import event_emitter
from app.models.events import (
    GPInterrogatingEvent,
    GPQuestionEvent,
    GPEvaluatingEvent,
    InterconsultationCreatedEvent,
    SpecialistStartedEvent,
    ToolStartedEvent,
    ToolCompletedEvent,
    SourceFoundEvent,
    SpecialistCompletedEvent,
    IntegratingEvent,
    CompletedEvent
)


class MedicalConsultationState(TypedDict):
    """State for the medical consultation workflow"""
    original_consultation: str
    patient_context: Dict[str, Any]
    consulta_id: str
    general_evaluation: Dict[str, Any] | None
    interrogation_questions: List[Dict[str, Any]]
    user_responses: Dict[str, Any] | None
    interrogation_completed: bool
    interconsultations: List[Dict[str, Any]]
    counter_referrals: List[Dict[str, Any]]
    clinical_record: Dict[str, Any] | None
    final_response: str | None
    status: str
    error: str | None


async def interrogate_patient(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: GP interrogates patient to gather necessary information.
    """
    consulta_id = state['consulta_id']

    await event_emitter.emit(GPInterrogatingEvent(
        consulta_id=consulta_id,
        data={
            "phase": "interrogation",
            "message": "GP gathering patient information"
        }
    ))

    contexto = PatientContext(**state['patient_context'])

    questions_data = await general_practitioner.generate_interrogation_questions(
        consultation=state['original_consultation'],
        patient_context=contexto
    )

    await event_emitter.emit(GPQuestionEvent(
        consulta_id=consulta_id,
        data={
            "questions": questions_data.get('questions', []),
            "reasoning": questions_data.get('reasoning', '')
        }
    ))

    consulta_db = await MedicalConsultation.get(consulta_id)
    if consulta_db:
        consulta_db.interrogation_questions = [InterrogationQuestion(**q) for q in questions_data.get('questions', [])]
        consulta_db.update_status('interrogating')
        consulta_db.add_trace("interrogate_patient", {"question_count": len(questions_data.get('questions', []))})
        await consulta_db.save()

    state['interrogation_questions'] = questions_data.get('questions', [])
    state['interrogation_completed'] = questions_data.get('can_proceed', False)
    state['status'] = 'interrogating' if not questions_data.get('can_proceed', False) else 'evaluating'

    return state


async def evaluate_initial_consultation(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: General practitioner evaluates the consultation.
    """
    consulta_id = state['consulta_id']

    await event_emitter.emit(GPEvaluatingEvent(
        consulta_id=consulta_id,
        data={
            "phase": "evaluation",
            "message": "GP evaluating consultation"
        }
    ))

    contexto = PatientContext(**state['patient_context'])

    if state.get('user_responses'):
        for key, value in state['user_responses'].items():
            if key in contexto.model_fields:
                setattr(contexto, key, value)

    evaluacion = await general_practitioner.evaluate_consultation(
        consultation=state['original_consultation'],
        patient_context=contexto
    )

    await event_emitter.emit(GPEvaluatingEvent(
        consulta_id=consulta_id,
        data={
            "can_answer_directly": evaluacion.can_answer_directly,
            "required_specialists": evaluacion.required_specialists,
            "complexity": evaluacion.estimated_complexity
        }
    ))

    consulta_db = await MedicalConsultation.get(consulta_id)
    if consulta_db:
        consulta_db.general_evaluation = evaluacion
        consulta_db.add_trace("evaluate_consultation", {
            "can_answer_directly": evaluacion.can_answer_directly,
            "specialists": evaluacion.required_specialists
        })
        await consulta_db.save()

    state['general_evaluation'] = evaluacion.model_dump()

    if evaluacion.can_answer_directly:
        state['status'] = 'completed'
        state['final_response'] = evaluacion.direct_response if hasattr(evaluacion, 'direct_response') else ''
    else:
        state['status'] = 'consulting'

    return state


async def generate_interconsultations(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: Generate interconsultation notes for specialists.
    """
    consulta_id = state['consulta_id']

    await event_emitter.emit(InterconsultationCreatedEvent(
        consulta_id=consulta_id,
        data={
            "phase": "generating_interconsultations",
            "message": "GP generating specialist notes"
        }
    ))

    evaluacion = GeneralEvaluation(**state['general_evaluation'])
    contexto = PatientContext(**state['patient_context'])

    interconsultations = []

    for specialty in evaluacion.required_specialists:
        await event_emitter.emit(InterconsultationCreatedEvent(
            consulta_id=consulta_id,
            data={
                "specialty": specialty
            }
        ))

        interconsultation = await general_practitioner.generate_interconsulta(
            specialty=specialty,
            consultation=state['original_consultation'],
            patient_context=contexto
        )

        interconsultations.append(interconsultation.model_dump())

    consulta_db = await MedicalConsultation.get(consulta_id)
    if consulta_db:
        for ic in interconsultations:
            consulta_db.add_interconsultation(InterconsultationNote(**ic))
        consulta_db.add_trace("generate_interconsultations", {"count": len(interconsultations)})
        await consulta_db.save()

    state['interconsultations'] = interconsultations

    return state


async def execute_specialists(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: Execute specialist agents in parallel.
    """
    consulta_id = state['consulta_id']

    await event_emitter.emit(SpecialistStartedEvent(
        consulta_id=consulta_id,
        data={
            "phase": "specialist_consultation",
            "message": "Specialists analyzing case"
        }
    ))

    contexto = PatientContext(**state['patient_context'])

    async def process_interconsulta(interconsulta_data: Dict[str, Any]) -> Dict[str, Any]:
        interconsultation = InterconsultationNote(**interconsulta_data)

        await event_emitter.emit(SpecialistStartedEvent(
            consulta_id=consulta_id,
            data={
                "specialty": interconsultation.specialty
            }
        ))

        async def on_tool_start(tool_name: str, specialty: str):
            await event_emitter.emit(ToolStartedEvent(
                consulta_id=consulta_id,
                data={
                    "tool": tool_name,
                    "specialty": specialty
                }
            ))

        async def on_tool_complete(tool_name: str, specialty: str):
            await event_emitter.emit(ToolCompletedEvent(
                consulta_id=consulta_id,
                data={
                    "tool": tool_name,
                    "specialty": specialty
                }
            ))

        async def on_source_found(source):
            await event_emitter.emit(SourceFoundEvent(
                consulta_id=consulta_id,
                data={
                    "source": source.model_dump()
                }
            ))

        specialist = get_specialist_agent(
            interconsultation.specialty,
            on_tool_start=on_tool_start,
            on_tool_complete=on_tool_complete,
            on_source_found=on_source_found
        )

        counter_referral = await specialist.process_interconsultation(
            interconsultation_id=interconsultation.id,
            question=interconsultation.specific_question,
            context=interconsultation.relevant_context,
            patient_context=contexto
        )

        await event_emitter.emit(SpecialistCompletedEvent(
            consulta_id=consulta_id,
            data={
                "specialty": interconsultation.specialty
            }
        ))

        return counter_referral.model_dump()

    tasks = [process_interconsulta(ic) for ic in state['interconsultations']]
    counter_referrals = await asyncio.gather(*tasks)

    consulta_db = await MedicalConsultation.get(consulta_id)
    if consulta_db:
        for contra_data in counter_referrals:
            consulta_db.add_counter_referral(CounterReferralNote(**contra_data))
        consulta_db.add_trace("execute_specialists", {"count": len(counter_referrals)})
        await consulta_db.save()

    state['counter_referrals'] = counter_referrals
    state['status'] = 'integrating'

    return state


async def integrate_responses(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: Integrate specialist responses into final answer.
    """
    consulta_id = state['consulta_id']

    await event_emitter.emit(IntegratingEvent(
        consulta_id=consulta_id,
        data={
            "phase": "integration",
            "message": "GP integrating specialist responses"
        }
    ))

    contexto = PatientContext(**state['patient_context'])
    counter_referrals = [CounterReferralNote(**c) for c in state['counter_referrals']]

    response_data = await general_practitioner.integrate_responses(
        consultation=state['original_consultation'],
        patient_context=contexto,
        counter_referrals=counter_referrals
    )

    interconsultations = [InterconsultationNote(**ic) for ic in state['interconsultations']]

    all_sources = []
    for contra in counter_referrals:
        all_sources.extend(contra.sources)

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

    clinical_record = ClinicalRecord(
        general_summary=response_data.get('general_summary', ''),
        complete_notes=expediente_text,
        final_response=response_data.get('final_response', ''),
        management_plan=response_data.get('management_plan'),
        recommended_followup=response_data.get('recommended_followup'),
        all_sources=all_sources
    )

    await event_emitter.emit(CompletedEvent(
        consulta_id=consulta_id,
        data={
            "final_response": response_data.get('final_response', ''),
            "sources_count": len(all_sources)
        }
    ))

    consulta_db = await MedicalConsultation.get(consulta_id)
    if consulta_db:
        consulta_db.clinical_record = clinical_record
        consulta_db.update_status('completed')
        consulta_db.add_trace("integrate_responses", {"expediente_generated": True})
        await consulta_db.save()

    state['clinical_record'] = clinical_record.model_dump()
    state['final_response'] = response_data.get('final_response', '')
    state['status'] = 'completed'

    return state


def should_interrogate(state: MedicalConsultationState) -> str:
    """Router: Decide if interrogation is needed."""
    if state.get('interrogation_completed'):
        return "evaluate"
    return "interrogate"


def should_consult_specialists(state: MedicalConsultationState) -> str:
    """Router: Decide if we need to consult specialists."""
    if state['general_evaluation']['can_answer_directly']:
        return "end"
    return "generate_interconsultations"


def create_workflow() -> StateGraph:
    """Create the medical consultation workflow graph."""
    workflow = StateGraph(MedicalConsultationState)

    workflow.add_node("interrogate", interrogate_patient)
    workflow.add_node("evaluate", evaluate_initial_consultation)
    workflow.add_node("generate_interconsultations", generate_interconsultations)
    workflow.add_node("execute_specialists", execute_specialists)
    workflow.add_node("integrate", integrate_responses)

    workflow.set_entry_point("interrogate")

    workflow.add_conditional_edges(
        "interrogate",
        should_interrogate,
        {
            "interrogate": END,
            "evaluate": "evaluate"
        }
    )

    workflow.add_conditional_edges(
        "evaluate",
        should_consult_specialists,
        {
            "generate_interconsultations": "generate_interconsultations",
            "end": END
        }
    )

    workflow.add_edge("generate_interconsultations", "execute_specialists")
    workflow.add_edge("execute_specialists", "integrate")
    workflow.add_edge("integrate", END)

    app = workflow.compile()

    return app


medical_consultation_workflow = create_workflow()
