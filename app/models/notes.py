"""
Templates y modelos para notes médicas formateadas.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PlantillaNotaInterconsulta(BaseModel):
    """Plantilla para generar nota de interconsultation"""
    specialty: str
    motivo: str
    antecedentes_relevantes: str
    contexto_clinico: str
    specific_question: str
    informacion_relevante: str
    expectativa: str

    def generar_nota(self) -> str:
        """Generates formatted interconsultation note"""
        return f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    INTERCONSULTATION NOTE TO {self.specialty.upper()}                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

REASON FOR INTERCONSULTATION:
{self.motivo}

RELEVANT MEDICAL HISTORY:
{self.antecedentes_relevantes}

CLINICAL CONTEXT:
{self.contexto_clinico}

SPECIFIC QUESTION:
{self.specific_question}

RELEVANT INFORMATION:
{self.informacion_relevante}

EXPECTATION:
{self.expectativa}

────────────────────────────────────────────────────────────────────────────────
Date and time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
────────────────────────────────────────────────────────────────────────────────
""".strip()


class PlantillaNotaContrarreferencia(BaseModel):
    """Template for generating counter-referral note"""
    specialty: str
    evaluation: str
    evidence_consulted: List[str]
    clinical_reasoning: str
    response: str
    recommendations: List[str]
    evidence_level: str
    additional_information_required: Optional[List[str]] = None

    def generar_nota(self) -> str:
        """Genera la nota de counter_referral formateada"""

        # Format evidence
        evidence_str = "\n".join([f"• {ev}" for ev in self.evidence_consulted])

        # Format recommendations
        recommendations_str = "\n".join([f"{i+1}. {rec}" for i, rec in enumerate(self.recommendations)])

        # Additional information if applicable
        additional_info_str = ""
        if self.additional_information_required:
            additional_info = "\n".join([f"• {info}" for info in self.additional_information_required])
            additional_info_str = f"""
ADDITIONAL INFORMATION REQUIRED:
{additional_info}
"""

        nota = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              COUNTER-REFERRAL NOTE - {self.specialty.upper()}                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

EVALUATION:
{self.evaluation}

EVIDENCE REVIEW:
{evidence_str}

CLINICAL REASONING:
{self.clinical_reasoning}

RESPONSE TO QUESTION:
{self.response}

RECOMMENDATIONS:
{recommendations_str}

EVIDENCE LEVEL:
{self.evidence_level}
{additional_info_str}
────────────────────────────────────────────────────────────────────────────────
Date and time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Specialist: {self.specialty}
────────────────────────────────────────────────────────────────────────────────
""".strip()

        return nota


class PlantillaExpedienteClinico(BaseModel):
    """Plantilla para generar clinical_record clínico completo"""
    original_consultation: str
    patient_context: str
    nota_medico_general: str
    interconsultations: List[tuple[str, str]]  # (nota_interconsulta, nota_contrarreferencia)
    final_response: str
    management_plan: Optional[List[str]] = None
    seguimiento: Optional[str] = None

    def generar_expediente(self) -> str:
        """Genera el clinical_record clínico completo formateado"""

        # Header
        clinical_record = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           CLINICAL RECORD                                    ║
║                    AI Medical Interconsultation System                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

DATE AND TIME: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

{'═' * 80}
ORIGINAL CONSULTATION
{'═' * 80}

{self.original_consultation}

PATIENT CONTEXT:
{self.patient_context}

{'═' * 80}
GENERAL PRACTITIONER NOTE - INITIAL EVALUATION
{'═' * 80}

{self.nota_medico_general}

"""

        # Interconsultations and counter-referrals
        if self.interconsultations:
            clinical_record += f"\n{'═' * 80}\n"
            clinical_record += "INTERCONSULTATIONS AND SPECIALIST RESPONSES\n"
            clinical_record += f"{'═' * 80}\n\n"

            for i, (nota_inter, nota_contra) in enumerate(self.interconsultations, 1):
                clinical_record += f"\n{'─' * 80}\n"
                clinical_record += f"INTERCONSULTATION #{i}\n"
                clinical_record += f"{'─' * 80}\n\n"
                clinical_record += nota_inter
                clinical_record += f"\n\n{'─' * 80}\n"
                clinical_record += f"SPECIALIST RESPONSE #{i}\n"
                clinical_record += f"{'─' * 80}\n\n"
                clinical_record += nota_contra
                clinical_record += "\n\n"

        # Final response
        clinical_record += f"\n{'═' * 80}\n"
        clinical_record += "INTEGRATION AND FINAL RESPONSE\n"
        clinical_record += f"{'═' * 80}\n\n"
        clinical_record += self.final_response
        clinical_record += "\n"

        # Management plan
        if self.management_plan:
            plan_str = "\n".join([f"{i+1}. {item}" for i, item in enumerate(self.management_plan)])
            clinical_record += f"\n{'─' * 80}\n"
            clinical_record += "MANAGEMENT PLAN\n"
            clinical_record += f"{'─' * 80}\n\n"
            clinical_record += plan_str
            clinical_record += "\n"

        # Follow-up
        if self.seguimiento:
            clinical_record += f"\n{'─' * 80}\n"
            clinical_record += "RECOMMENDED FOLLOW-UP\n"
            clinical_record += f"{'─' * 80}\n\n"
            clinical_record += self.seguimiento
            clinical_record += "\n"

        # Footer
        clinical_record += f"\n{'═' * 80}\n"
        clinical_record += "END OF RECORD\n"
        clinical_record += f"{'═' * 80}\n"

        return clinical_record


class FormatoContextoPaciente:
    """Formats patient context for notes"""

    @staticmethod
    def formatear(contexto: dict) -> str:
        """Formats patient context"""
        partes = []

        if contexto.get("age"):
            sex = contexto.get("sex", "").capitalize()
            partes.append(f"• Patient {sex.lower()} {contexto['age']} years old")

        if contexto.get("diagnoses"):
            diags = ", ".join(contexto["diagnoses"])
            partes.append(f"• Diagnoses: {diags}")

        if contexto.get("current_medications"):
            meds = "\n  - " + "\n  - ".join(contexto["current_medications"])
            partes.append(f"• Current medications:{meds}")

        if contexto.get("allergies"):
            if contexto["allergies"]:
                alers = ", ".join(contexto["allergies"])
                partes.append(f"• Allergies: {alers}")
            else:
                partes.append("• No known allergies")

        if contexto.get("lab_results"):
            labs = "\n  - ".join([f"{k}: {v}" for k, v in contexto["lab_results"].items()])
            partes.append(f"• Laboratory results:\n  - {labs}")

        if contexto.get("vital_signs"):
            sv = ", ".join([f"{k}: {v}" for k, v in contexto["vital_signs"].items()])
            partes.append(f"• Vital signs: {sv}")

        return "\n".join(partes)
