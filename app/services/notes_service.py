"""
Servicio para generación de notes médicas.
"""
from typing import List, Dict, Any
from app.models.notes import (
    PlantillaNotaInterconsulta,
    PlantillaNotaContrarreferencia,
    PlantillaExpedienteClinico,
    FormatoContextoPaciente
)
from app.models.consultation import (
    InterconsultationNote,
    CounterReferralNote,
    PatientContext
)


class NotasService:
    """Servicio para generar notes médicas formateadas"""

    @staticmethod
    def generar_nota_interconsulta(
        specialty: str,
        original_consultation: str,
        patient_context: PatientContext,
        specific_question: str,
        relevant_context: Dict[str, Any]
    ) -> str:
        """
        Genera una nota de interconsultation formateada.

        Args:
            specialty: Especialidad médica
            original_consultation: Consulta original del usuario
            patient_context: Contexto del paciente
            specific_question: Pregunta específica para el especialista
            relevant_context: Contexto relevante extraído

        Returns:
            Nota de interconsultation formateada
        """
        # Formatear contexto del paciente
        contexto_str = FormatoContextoPaciente.formatear(patient_context.model_dump())

        # Create template
        plantilla = PlantillaNotaInterconsulta(
            specialty=specialty,
            motivo=f"Interconsultation for specialized evaluation in {specialty}",
            antecedentes_relevantes=relevant_context.get("background", relevant_context.get("antecedentes", contexto_str)),
            contexto_clinico=original_consultation,
            specific_question=specific_question,
            informacion_relevante=contexto_str,
            expectativa=relevant_context.get(
                "expectation",
                relevant_context.get("expectativa",
                    f"Evaluation from {specialty} perspective and evidence-based recommendations requested."
                )
            )
        )

        return plantilla.generar_nota()

    @staticmethod
    def generar_nota_contrarreferencia(
        counter_referral: CounterReferralNote
    ) -> str:
        """
        Genera una nota de counter_referral formateada.

        Args:
            counter_referral: Objeto con datos de counter_referral

        Returns:
            Nota de counter_referral formateada
        """
        plantilla = PlantillaNotaContrarreferencia(
            specialty=counter_referral.specialty,
            evaluation=counter_referral.evaluation,
            evidence_consulted=counter_referral.evidence_used,
            clinical_reasoning=counter_referral.clinical_reasoning,
            response=counter_referral.response,
            recommendations=counter_referral.recommendations,
            evidence_level=counter_referral.evidence_level,
            additional_information_required=(
                counter_referral.additional_questions
                if counter_referral.requires_additional_info
                else None
            )
        )

        return plantilla.generar_nota()

    @staticmethod
    def generar_expediente_completo(
        original_consultation: str,
        patient_context: PatientContext,
        nota_medico_general: str,
        interconsultations: List[InterconsultationNote],
        counter_referrals: List[CounterReferralNote],
        final_response: str,
        management_plan: List[str] = None,
        seguimiento: str = None
    ) -> str:
        """
        Genera el clinical_record clínico completo.

        Args:
            original_consultation: Consulta original
            patient_context: Contexto del paciente
            nota_medico_general: Nota del médico general
            interconsultations: Lista de interconsultations
            counter_referrals: Lista de counter_referrals
            final_response: Respuesta final integrada
            management_plan: Plan de manejo
            seguimiento: Recomendaciones de seguimiento

        Returns:
            Expediente clínico completo formateado
        """
        # Formatear contexto del paciente
        contexto_str = FormatoContextoPaciente.formatear(patient_context.model_dump())

        # Emparejar interconsultations con counter_referrals
        pares_notas = []

        for interconsultation in interconsultations:
            # Buscar counter_referral correspondiente
            contra = None
            for c in counter_referrals:
                if c.interconsultation_id == interconsultation.id:
                    contra = c
                    break

            if contra:
                # Generar notes formateadas
                nota_inter = NotasService.generar_nota_interconsulta(
                    specialty=interconsultation.specialty,
                    original_consultation=original_consultation,
                    patient_context=patient_context,
                    specific_question=interconsultation.specific_question,
                    relevant_context=interconsultation.relevant_context
                )

                nota_contra = NotasService.generar_nota_contrarreferencia(contra)

                pares_notas.append((nota_inter, nota_contra))

        # Crear clinical_record
        plantilla = PlantillaExpedienteClinico(
            original_consultation=original_consultation,
            patient_context=contexto_str,
            nota_medico_general=nota_medico_general,
            interconsultations=pares_notas,
            final_response=final_response,
            management_plan=management_plan,
            seguimiento=seguimiento
        )

        return plantilla.generar_expediente()

    @staticmethod
    def extraer_fuentes(counter_referrals: List[CounterReferralNote]) -> List[str]:
        """
        Extrae todas las fuentes de evidencia utilizadas.

        Args:
            counter_referrals: Lista de counter_referrals

        Returns:
            Lista única de fuentes
        """
        fuentes = set()

        for contra in counter_referrals:
            fuentes.update(contra.evidence_used)

        return sorted(list(fuentes))

    @staticmethod
    def generar_resumen_ejecutivo(
        consultation: str,
        counter_referrals: List[CounterReferralNote],
        final_response: str
    ) -> str:
        """
        Genera un resumen ejecutivo breve.

        Args:
            consultation: Consulta original
            counter_referrals: Contrarreferencias recibidas
            final_response: Respuesta final

        Returns:
            Resumen ejecutivo
        """
        specialists = [c.specialty for c in counter_referrals]
        especialistas_str = ", ".join(specialists)

        resumen = f"""
EXECUTIVE SUMMARY

Consultation: {consultation}

Specialists consulted: {especialistas_str}

Response:
{final_response}

Total specialists involved: {len(counter_referrals)}
""".strip()

        return resumen


# Instancia global del servicio
notas_service = NotasService()
