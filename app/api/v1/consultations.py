"""
Consultation endpoints.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.models.consultation import (
    ConsultaCreate,
    ConsultaResponse,
    InformacionAdicional,
    ConsultaCompleta
)
from app.models.database import MedicalConsultation
from app.agents.graph import medical_consultation_workflow, MedicalConsultationState

router = APIRouter()


@router.post("/consultation", response_model=ConsultaResponse, status_code=status.HTTP_201_CREATED)
async def create_consulta(consulta_data: ConsultaCreate):
    """
    Create a new medical consultation.

    This endpoint initiates a new consultation which will be evaluated by the
    general practitioner agent and routed to appropriate specialists if needed.

    Args:
        consulta_data: Consultation data

    Returns:
        Consultation response with ID and status
    """
    # Create consultation in database
    consulta_db = MedicalConsultation(
        usuario_id=consulta_data.usuario_id,
        original_consultation=consulta_data.consultation,
        patient_context=consulta_data.contexto,
        estado="evaluando"
    )

    await consulta_db.insert()

    # Prepare initial state for workflow
    initial_state: MedicalConsultationState = {
        "original_consultation": consulta_data.consultation,
        "patient_context": consulta_data.contexto.model_dump(),
        "consulta_id": str(consulta_db.id),
        "general_evaluation": None,
        "interconsultations": [],
        "counter_referrals": [],
        "pending_questions": [],
        "additional_information": None,
        "clinical_record": None,
        "final_response": None,
        "estado": "evaluando",
        "error": None
    }

    try:
        # Execute workflow
        final_state = await medical_consultation_workflow.ainvoke(initial_state)

        # Check if waiting for additional information
        if final_state.get('estado') == 'waiting_info':
            return ConsultaResponse(
                consulta_id=str(consulta_db.id),
                estado="esperando_info",
                mensaje="Additional information required from specialists",
                progreso={
                    "pending_questions": final_state.get('pending_questions', [])
                }
            )

        # Check if completed
        elif final_state.get('estado') == 'completed':
            # Refresh from database to get complete data
            consulta_db = await MedicalConsultation.get(consulta_db.id)

            return ConsultaResponse(
                consulta_id=str(consulta_db.id),
                estado="completado",
                mensaje="Consultation completed successfully",
                clinical_record=consulta_db.clinical_record
            )

        else:
            return ConsultaResponse(
                consulta_id=str(consulta_db.id),
                estado=final_state.get('estado', 'procesando'),
                mensaje="Consultation in progress"
            )

    except Exception as e:
        # Update database with error
        consulta_db.error_message = str(e)
        consulta_db.actualizar_estado("error")
        await consulta_db.save()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing consultation: {str(e)}"
        )


@router.get("/consultation/{consulta_id}", response_model=ConsultaCompleta)
async def get_consulta(consulta_id: str):
    """
    Get complete consultation details.

    Args:
        consulta_id: Consultation ID

    Returns:
        Complete consultation data
    """
    consultation = await MedicalConsultation.get(consulta_id)

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation not found: {consulta_id}"
        )

    return ConsultaCompleta(
        consulta_id=str(consultation.id),
        usuario_id=consultation.usuario_id,
        original_consultation=consultation.original_consultation,
        patient_context=consultation.patient_context,
        estado=consultation.estado,
        timestamp=consultation.created_at,
        general_evaluation=consultation.general_evaluation,
        interconsultations=consultation.interconsultations,
        counter_referrals=consultation.counter_referrals,
        clinical_record=consultation.clinical_record,
        created_at=consultation.created_at,
        updated_at=consultation.updated_at
    )


@router.post("/consultation/{consulta_id}/responder", response_model=ConsultaResponse)
async def responder_consulta(consulta_id: str, info: InformacionAdicional):
    """
    Provide additional information requested by specialists.

    Args:
        consulta_id: Consultation ID
        info: Additional information

    Returns:
        Updated consultation response
    """
    consultation = await MedicalConsultation.get(consulta_id)

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation not found: {consulta_id}"
        )

    if consultation.estado != "esperando_info":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Consultation is not waiting for information. Current status: {consultation.estado}"
        )

    # Update additional information
    consultation.additional_information = info.additional_information
    consultation.pending_questions = []
    consultation.actualizar_estado("procesando")
    await consultation.save()

    # TODO: Resume workflow with additional information
    # This would require implementing workflow resumption
    # For now, return success message

    return ConsultaResponse(
        consulta_id=str(consultation.id),
        estado="procesando",
        mensaje="Additional information received. Processing continues..."
    )


@router.get("/consultation/{consulta_id}/estado")
async def get_estado_consulta(consulta_id: str) -> Dict[str, Any]:
    """
    Get consultation status.

    Args:
        consulta_id: Consultation ID

    Returns:
        Status information
    """
    consultation = await MedicalConsultation.get(consulta_id)

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation not found: {consulta_id}"
        )

    return {
        "consulta_id": str(consultation.id),
        "estado": consultation.estado,
        "created_at": consultation.created_at,
        "updated_at": consultation.updated_at,
        "completed_at": consultation.completed_at,
        "progress": {
            "evaluacion_completada": consultation.general_evaluation is not None,
            "interconsultas_generadas": len(consultation.interconsultations),
            "contrarreferencias_recibidas": len(consultation.counter_referrals),
            "expediente_generado": consultation.clinical_record is not None
        },
        "pending_questions": consultation.pending_questions,
        "error": consultation.error_message
    }
