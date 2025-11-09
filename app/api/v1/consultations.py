"""
Consultation endpoints.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, List
from pydantic import BaseModel

from app.models.consultation import (
    ConsultationCreate,
    ConsultationResponse,
    AdditionalInformation,
    CompleteConsultation
)
from app.models.sources import ScientificSource
from app.models.database import MedicalConsultation
from app.agents.graph import medical_consultation_workflow, MedicalConsultationState

router = APIRouter()


class InterrogationResponse(BaseModel):
    """Response model for interrogation answers"""
    responses: Dict[str, Any]


@router.post("/consultation", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
async def create_consultation(consultation_data: ConsultationCreate):
    """
    Create a new medical consultation.
    """
    consultation_db = MedicalConsultation(
        user_id=consultation_data.user_id,
        original_consultation=consultation_data.consultation,
        patient_context=consultation_data.context,
        status="interrogating"
    )

    await consultation_db.insert()

    initial_state: MedicalConsultationState = {
        "original_consultation": consultation_data.consultation,
        "patient_context": consultation_data.context.model_dump(),
        "consulta_id": str(consultation_db.id),
        "general_evaluation": None,
        "interrogation_questions": [],
        "user_responses": None,
        "interrogation_completed": False,
        "interconsultations": [],
        "counter_referrals": [],
        "clinical_record": None,
        "final_response": None,
        "status": "interrogating",
        "error": None
    }

    try:
        final_state = await medical_consultation_workflow.ainvoke(initial_state)

        if final_state.get('status') == 'interrogating':
            return ConsultationResponse(
                consultation_id=str(consultation_db.id),
                status="interrogating",
                message="GP needs additional patient information",
                progress={
                    "interrogation_questions": final_state.get('interrogation_questions', [])
                }
            )

        elif final_state.get('status') == 'completed':
            consultation_db = await MedicalConsultation.get(consultation_db.id)

            return ConsultationResponse(
                consultation_id=str(consultation_db.id),
                status="completed",
                message="Consultation completed successfully",
                clinical_record=consultation_db.clinical_record
            )

        else:
            return ConsultationResponse(
                consultation_id=str(consultation_db.id),
                status=final_state.get('status', 'processing'),
                message="Consultation in progress"
            )

    except Exception as e:
        consultation_db.error_message = str(e)
        consultation_db.update_status("error")
        await consultation_db.save()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing consultation: {str(e)}"
        )


@router.get("/consultation/{consultation_id}", response_model=CompleteConsultation)
async def get_consultation(consultation_id: str):
    """
    Get complete consultation details.
    """
    consultation = await MedicalConsultation.get(consultation_id)

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation not found: {consultation_id}"
        )

    return CompleteConsultation(
        consultation_id=str(consultation.id),
        user_id=consultation.user_id,
        original_consultation=consultation.original_consultation,
        patient_context=consultation.patient_context,
        status=consultation.status,
        timestamp=consultation.created_at,
        interrogation_questions=consultation.interrogation_questions,
        interrogation_completed=consultation.interrogation_completed,
        general_evaluation=consultation.general_evaluation,
        interconsultations=consultation.interconsultations,
        counter_referrals=consultation.counter_referrals,
        clinical_record=consultation.clinical_record,
        created_at=consultation.created_at,
        updated_at=consultation.updated_at
    )


@router.post("/consultation/{consultation_id}/respond", response_model=ConsultationResponse)
async def respond_to_interrogation(consultation_id: str, response: InterrogationResponse):
    """
    Provide responses to GP interrogation questions.
    """
    consultation = await MedicalConsultation.get(consultation_id)

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation not found: {consultation_id}"
        )

    if consultation.status != "interrogating":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Consultation is not in interrogation phase. Current status: {consultation.status}"
        )

    consultation.user_responses = response.responses
    consultation.interrogation_completed = True
    consultation.update_status("evaluating")
    await consultation.save()

    resume_state: MedicalConsultationState = {
        "original_consultation": consultation.original_consultation,
        "patient_context": consultation.patient_context.model_dump(),
        "consulta_id": str(consultation.id),
        "general_evaluation": None,
        "interrogation_questions": [],
        "user_responses": response.responses,
        "interrogation_completed": True,
        "interconsultations": [],
        "counter_referrals": [],
        "clinical_record": None,
        "final_response": None,
        "status": "evaluating",
        "error": None
    }

    try:
        final_state = await medical_consultation_workflow.ainvoke(resume_state)

        if final_state.get('status') == 'completed':
            consultation = await MedicalConsultation.get(consultation.id)

            return ConsultationResponse(
                consultation_id=str(consultation.id),
                status="completed",
                message="Consultation completed successfully",
                clinical_record=consultation.clinical_record
            )

        else:
            return ConsultationResponse(
                consultation_id=str(consultation.id),
                status=final_state.get('status', 'processing'),
                message="Consultation in progress"
            )

    except Exception as e:
        consultation.error_message = str(e)
        consultation.update_status("error")
        await consultation.save()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing consultation: {str(e)}"
        )


@router.get("/consultation/{consultation_id}/sources", response_model=List[ScientificSource])
async def get_consultation_sources(consultation_id: str):
    """
    Get all scientific sources used in consultation.
    """
    consultation = await MedicalConsultation.get(consultation_id)

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation not found: {consultation_id}"
        )

    all_sources = []

    if consultation.counter_referrals:
        for counter_referral in consultation.counter_referrals:
            if hasattr(counter_referral, 'sources'):
                all_sources.extend(counter_referral.sources)

    if consultation.clinical_record and hasattr(consultation.clinical_record, 'all_sources'):
        all_sources = consultation.clinical_record.all_sources

    return all_sources


@router.get("/consultation/{consultation_id}/status")
async def get_consultation_status(consultation_id: str) -> Dict[str, Any]:
    """
    Get consultation status.
    """
    consultation = await MedicalConsultation.get(consultation_id)

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation not found: {consultation_id}"
        )

    return {
        "consultation_id": str(consultation.id),
        "status": consultation.status,
        "created_at": consultation.created_at,
        "updated_at": consultation.updated_at,
        "completed_at": consultation.completed_at,
        "progress": {
            "interrogation_completed": consultation.interrogation_completed if hasattr(consultation, 'interrogation_completed') else False,
            "evaluation_completed": consultation.general_evaluation is not None,
            "interconsultations_generated": len(consultation.interconsultations),
            "counter_referrals_received": len(consultation.counter_referrals),
            "clinical_record_generated": consultation.clinical_record is not None
        },
        "error": consultation.error_message
    }
