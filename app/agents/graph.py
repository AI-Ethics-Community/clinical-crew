"""
LangGraph workflow for multi-agent medical consultation system with event streaming.
"""
import time
import logging
from app.utils.logging import get_consultation_logger

# Setup module logger
logger = logging.getLogger("clinical_crew")

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
    node_logger = get_consultation_logger(consulta_id)
    start_time = time.time()
    
    node_logger.info("=== INICIANDO NODO: Evaluate Initial Consultation ===")

    try:
        await event_emitter.emit(GPEvaluatingEvent(
            consulta_id=consulta_id,
            data={
                "phase": "evaluation",
                "message": "GP evaluating consultation"
            }
        ))

        contexto = PatientContext(**state['patient_context'])

        if state.get('user_responses'):
            node_logger.debug(f"Applying user responses: {list(state['user_responses'].keys())}")
            for key, value in state['user_responses'].items():
                if key in contexto.model_fields:
                    setattr(contexto, key, value)

        node_logger.info("Calling GP to evaluate consultation")
        evaluacion = await general_practitioner.evaluate_consultation(
            consultation=state['original_consultation'],
            patient_context=contexto
        )

        node_logger.info(f"Evaluation complete: can_answer={evaluacion.can_answer_directly}, specialists={evaluacion.required_specialists}, complexity={evaluacion.estimated_complexity}")

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
            node_logger.debug("Evaluation saved to database")

        state['general_evaluation'] = evaluacion.model_dump()

        if evaluacion.can_answer_directly:
            node_logger.info("GP can answer directly, will generate direct response")
            state['status'] = 'integrating'
        else:
            node_logger.info(f"Will consult {len(evaluacion.required_specialists)} specialists")
            state['status'] = 'interconsulting'

        elapsed = time.time() - start_time
        node_logger.info(f"=== FINALIZANDO NODO: Evaluate Initial Consultation ({elapsed:.2f}s) ===")

        return state
        
    except Exception as e:
        elapsed = time.time() - start_time
        node_logger.error(f"Error in evaluate_initial_consultation after {elapsed:.2f}s: {str(e)}", exc_info=True)
        
        # Update consultation status to error
        consulta_db = await MedicalConsultation.get(consulta_id)
        if consulta_db:
            consulta_db.update_status('error')
            consulta_db.error_message = f"Error evaluating consultation: {str(e)}"
            await consulta_db.save()
        
        state['status'] = 'error'
        state['error'] = str(e)
        raise


async def generate_interconsultations(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: Generate interconsultation notes for specialists.
    """
    consulta_id = state['consulta_id']
    node_logger = get_consultation_logger(consulta_id)
    start_time = time.time()
    
    node_logger.info("=== INICIANDO NODO: Generate Interconsultations ===")

    try:
        await event_emitter.emit(InterconsultationCreatedEvent(
            consulta_id=consulta_id,
            data={
                "phase": "generating_interconsultations",
                "message": "GP generating specialist notes"
            }
        ))

        # Update DB status
        consulta_db = await MedicalConsultation.get(consulta_id)
        if consulta_db:
            consulta_db.update_status('interconsulting')
            await consulta_db.save()

        evaluacion = GeneralEvaluation(**state['general_evaluation'])
        contexto = PatientContext(**state['patient_context'])

        node_logger.info(f"Generating interconsultations for {len(evaluacion.required_specialists)} specialists")
        interconsultations = []

        for idx, specialty in enumerate(evaluacion.required_specialists, 1):
            node_logger.info(f"[{idx}/{len(evaluacion.required_specialists)}] Generating interconsultation for: {specialty}")
            
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
            node_logger.debug(f"Interconsultation created for {specialty}: {interconsultation.id}")

        consulta_db = await MedicalConsultation.get(consulta_id)
        if consulta_db:
            for ic in interconsultations:
                consulta_db.add_interconsultation(InterconsultationNote(**ic))
            consulta_db.add_trace("generate_interconsultations", {"count": len(interconsultations)})
            await consulta_db.save()

        state['interconsultations'] = interconsultations
        
        elapsed = time.time() - start_time
        node_logger.info(f"=== FINALIZANDO NODO: Generate Interconsultations ({elapsed:.2f}s, {len(interconsultations)} created) ===")

        return state
        
    except Exception as e:
        elapsed = time.time() - start_time
        node_logger.error(f"Error in generate_interconsultations after {elapsed:.2f}s: {str(e)}", exc_info=True)
        
        consulta_db = await MedicalConsultation.get(consulta_id)
        if consulta_db:
            consulta_db.update_status('error')
            consulta_db.error_message = f"Error generating interconsultations: {str(e)}"
            await consulta_db.save()
        
        state['status'] = 'error'
        state['error'] = str(e)
        raise


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


async def create_direct_response(state: MedicalConsultationState) -> MedicalConsultationState:
    """
    Node: Create clinical record when GP can answer directly without specialists.
    """
    consulta_id = state['consulta_id']
    node_logger = get_consultation_logger(consulta_id)
    start_time = time.time()

    node_logger.info("=== INICIANDO NODO: Create Direct Response ===")

    try:
        await event_emitter.emit(IntegratingEvent(
            consulta_id=consulta_id,
            data={
                "phase": "direct_response",
                "message": "GP generating direct response"
            }
        ))

        consulta_db = await MedicalConsultation.get(consulta_id)
        if consulta_db:
            consulta_db.update_status('integrating')
            consulta_db.add_trace("create_direct_response", {"direct_answer": True})
            await consulta_db.save()

        contexto = PatientContext(**state['patient_context'])
        general_evaluation = GeneralEvaluation(**state['general_evaluation'])

        node_logger.info("GP can answer directly, generating clinical response")
        
        # IMPORTANT: Generate actual clinical response using dedicated direct response method
        response_data = await general_practitioner.generate_direct_response(
            consultation=state['original_consultation'],
            patient_context=contexto
        )
        
        final_response = response_data.get('final_response', general_evaluation.reasoning)
        general_summary = response_data.get('general_summary', general_evaluation.reasoning)
        management_plan = response_data.get('management_plan')
        followup = response_data.get('recommended_followup')
        
        node_logger.debug(f"Generated direct response length: {len(final_response)} chars")
        
        # Create clinical record without specialist input
        expediente_text = notas_service.generar_expediente_completo(
            original_consultation=state['original_consultation'],
            patient_context=contexto,
            nota_medico_general=general_summary,
            interconsultations=[],
            counter_referrals=[],
            final_response=final_response,
            management_plan=management_plan,
            seguimiento=followup
        )

        clinical_record = ClinicalRecord(
            general_summary=general_summary,
            complete_notes=expediente_text,
            final_response=final_response,
            management_plan=management_plan,
            recommended_followup=followup,
            all_sources=[]
        )

        await event_emitter.emit(CompletedEvent(
            consulta_id=consulta_id,
            data={
                "final_response": final_response,
                "sources_count": 0
            }
        ))

        if consulta_db:
            consulta_db.clinical_record = clinical_record
            consulta_db.update_status('completed')
            consulta_db.add_trace("create_direct_response_completed", {"expediente_generated": True})
            await consulta_db.save()

        state['clinical_record'] = clinical_record.model_dump()
        state['final_response'] = final_response
        state['status'] = 'completed'
        
        elapsed = time.time() - start_time
        node_logger.info(f"=== FINALIZANDO NODO: Create Direct Response ({elapsed:.2f}s) ===")

        return state
        
    except Exception as e:
        elapsed = time.time() - start_time
        node_logger.error(f"Error in create_direct_response after {elapsed:.2f}s: {str(e)}", exc_info=True)
        
        consulta_db = await MedicalConsultation.get(consulta_id)
        if consulta_db:
            consulta_db.update_status('error')
            consulta_db.error_message = f"Error creating direct response: {str(e)}"
            await consulta_db.save()
        
        state['status'] = 'error'
        state['error'] = str(e)
        raise


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

    consulta_db = await MedicalConsultation.get(consulta_id)
    if consulta_db:
        consulta_db.update_status('integrating')
        consulta_db.add_trace("integrate_responses_start", {"counter_referrals_count": len(state['counter_referrals'])})
        await consulta_db.save()

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
    consulta_id = state.get('consulta_id', 'unknown')
    node_logger = get_consultation_logger(consulta_id)
    
    general_eval = state.get('general_evaluation', {})
    can_answer = general_eval.get('can_answer_directly', False)
    required_specialists = general_eval.get('required_specialists', [])
    
    node_logger.info(f"Routing decision: can_answer_directly={can_answer}, required_specialists={required_specialists}")
    
    if can_answer:
        node_logger.info("→ Routing to direct_response (GP can answer without specialists)")
        return "direct_response"
    else:
        node_logger.info(f"→ Routing to generate_interconsultations ({len(required_specialists)} specialists needed)")
        return "generate_interconsultations"


def create_workflow() -> StateGraph:
    """Create the medical consultation workflow graph."""
    workflow = StateGraph(MedicalConsultationState)

    workflow.add_node("interrogate", interrogate_patient)
    workflow.add_node("evaluate", evaluate_initial_consultation)
    workflow.add_node("direct_response", create_direct_response)
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
            "direct_response": "direct_response"
        }
    )

    workflow.add_edge("generate_interconsultations", "execute_specialists")
    workflow.add_edge("execute_specialists", "integrate")
    workflow.add_edge("integrate", END)
    workflow.add_edge("direct_response", END)

    app = workflow.compile()

    return app


medical_consultation_workflow = create_workflow()


def create_workflow_from_evaluation() -> StateGraph:
    """Create workflow that starts from evaluation phase (after interrogation)."""
    workflow = StateGraph(MedicalConsultationState)

    workflow.add_node("evaluate", evaluate_initial_consultation)
    workflow.add_node("direct_response", create_direct_response)
    workflow.add_node("generate_interconsultations", generate_interconsultations)
    workflow.add_node("execute_specialists", execute_specialists)
    workflow.add_node("integrate", integrate_responses)

    workflow.set_entry_point("evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        should_consult_specialists,
        {
            "generate_interconsultations": "generate_interconsultations",
            "direct_response": "direct_response"
        }
    )

    workflow.add_edge("generate_interconsultations", "execute_specialists")
    workflow.add_edge("execute_specialists", "integrate")
    workflow.add_edge("integrate", END)
    workflow.add_edge("direct_response", END)

    app = workflow.compile()

    return app


medical_consultation_workflow_from_evaluation = create_workflow_from_evaluation()
