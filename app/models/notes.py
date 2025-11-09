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
        """Genera la nota de interconsultation formateada"""
        return f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    NOTA DE INTERCONSULTA A {self.specialty.upper()}                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

MOTIVO DE INTERCONSULTA:
{self.motivo}

ANTECEDENTES RELEVANTES:
{self.antecedentes_relevantes}

CONTEXTO CLÍNICO:
{self.contexto_clinico}

PREGUNTA ESPECÍFICA:
{self.specific_question}

INFORMACIÓN RELEVANTE:
{self.informacion_relevante}

EXPECTATIVA:
{self.expectativa}

────────────────────────────────────────────────────────────────────────────────
Fecha y hora: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
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
║              NOTA DE CONTRARREFERENCIA - {self.specialty.upper()}                    ║
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
Fecha y hora: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
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
║                           EXPEDIENTE CLÍNICO                                 ║
║                    Sistema de Interconsulta Médica IA                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

FECHA Y HORA: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

{'═' * 80}
CONSULTA ORIGINAL
{'═' * 80}

{self.original_consultation}

CONTEXTO DEL PACIENTE:
{self.patient_context}

{'═' * 80}
NOTA DEL MÉDICO GENERAL - EVALUACIÓN INICIAL
{'═' * 80}

{self.nota_medico_general}

"""

        # Interconsultas y counter_referrals
        if self.interconsultations:
            clinical_record += f"\n{'═' * 80}\n"
            clinical_record += "INTERCONSULTAS Y RESPUESTAS DE ESPECIALISTAS\n"
            clinical_record += f"{'═' * 80}\n\n"

            for i, (nota_inter, nota_contra) in enumerate(self.interconsultations, 1):
                clinical_record += f"\n{'─' * 80}\n"
                clinical_record += f"INTERCONSULTA #{i}\n"
                clinical_record += f"{'─' * 80}\n\n"
                clinical_record += nota_inter
                clinical_record += f"\n\n{'─' * 80}\n"
                clinical_record += f"RESPUESTA ESPECIALISTA #{i}\n"
                clinical_record += f"{'─' * 80}\n\n"
                clinical_record += nota_contra
                clinical_record += "\n\n"

        # Respuesta final
        clinical_record += f"\n{'═' * 80}\n"
        clinical_record += "INTEGRACIÓN Y RESPUESTA FINAL\n"
        clinical_record += f"{'═' * 80}\n\n"
        clinical_record += self.final_response
        clinical_record += "\n"

        # Plan de manejo
        if self.management_plan:
            plan_str = "\n".join([f"{i+1}. {item}" for i, item in enumerate(self.management_plan)])
            clinical_record += f"\n{'─' * 80}\n"
            clinical_record += "PLAN DE MANEJO\n"
            clinical_record += f"{'─' * 80}\n\n"
            clinical_record += plan_str
            clinical_record += "\n"

        # Seguimiento
        if self.seguimiento:
            clinical_record += f"\n{'─' * 80}\n"
            clinical_record += "SEGUIMIENTO RECOMENDADO\n"
            clinical_record += f"{'─' * 80}\n\n"
            clinical_record += self.seguimiento
            clinical_record += "\n"

        # Footer
        clinical_record += f"\n{'═' * 80}\n"
        clinical_record += "FIN DEL EXPEDIENTE\n"
        clinical_record += f"{'═' * 80}\n"

        return clinical_record


class FormatoContextoPaciente:
    """Formatea el contexto del paciente para las notes"""

    @staticmethod
    def formatear(contexto: dict) -> str:
        """Formatea el contexto del paciente"""
        partes = []

        if contexto.get("edad"):
            sexo = contexto.get("sexo", "").capitalize()
            partes.append(f"• Paciente {sexo.lower()} de {contexto['edad']} años")

        if contexto.get("diagnosticos"):
            diags = ", ".join(contexto["diagnosticos"])
            partes.append(f"• Diagnósticos: {diags}")

        if contexto.get("medicamentos_actuales"):
            meds = "\n  - " + "\n  - ".join(contexto["medicamentos_actuales"])
            partes.append(f"• Medicamentos actuales:{meds}")

        if contexto.get("alergias"):
            if contexto["alergias"]:
                alers = ", ".join(contexto["alergias"])
                partes.append(f"• Alergias: {alers}")
            else:
                partes.append("• Sin alergias conocidas")

        if contexto.get("laboratorios"):
            labs = "\n  - ".join([f"{k}: {v}" for k, v in contexto["laboratorios"].items()])
            partes.append(f"• Laboratorios:\n  - {labs}")

        if contexto.get("signos_vitales"):
            sv = ", ".join([f"{k}: {v}" for k, v in contexto["signos_vitales"].items()])
            partes.append(f"• Signos vitales: {sv}")

        return "\n".join(partes)
