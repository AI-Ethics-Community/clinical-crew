"""
Cliente para Google Gemini AI.
"""
import google.generativeai as genai
from typing import Optional, Dict, Any, List
from app.config.settings import settings


class GeminiClient:
    """Cliente para interactuar con Google Gemini"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None
    ):
        """
        Inicializa el cliente de Gemini.

        Args:
            model_name: Nombre del modelo (usa settings por defecto)
            temperature: Temperatura del modelo
            max_output_tokens: Máximo de tokens de salida
        """
        genai.configure(api_key=settings.gemini_api_key)

        self.model_name = model_name or settings.gemini_pro_model
        self.temperature = temperature or settings.gemini_temperature
        self.max_output_tokens = max_output_tokens or settings.gemini_max_output_tokens

        # Configuración de generación
        self.generation_config = genai.GenerationConfig(
            temperature=self.temperature,
            top_p=settings.gemini_top_p,
            top_k=settings.gemini_top_k,
            max_output_tokens=self.max_output_tokens,
        )

        # Configuraciones de seguridad (permisivas para contenido médico)
        self.safety_settings = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
        }

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Genera contenido con Gemini.

        Args:
            prompt: Prompt del usuario
            system_instruction: Instrucción del sistema
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta generada
        """
        # Crear modelo
        model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            system_instruction=system_instruction
        )

        # Generar
        response = model.generate_content(prompt, **kwargs)

        return response.text

    def generate_with_retry(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        Genera contenido con reintentos en caso de error.

        Args:
            prompt: Prompt del usuario
            system_instruction: Instrucción del sistema
            max_retries: Número máximo de reintentos
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta generada
        """
        for attempt in range(max_retries):
            try:
                return self.generate_content(prompt, system_instruction, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"Reintento {attempt + 1}/{max_retries} después de error: {str(e)}")

        raise Exception("Max retries exceeded")

    async def generate_content_async(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Genera contenido de forma asíncrona.

        Args:
            prompt: Prompt del usuario
            system_instruction: Instrucción del sistema
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta generada
        """
        # Crear modelo
        model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            system_instruction=system_instruction
        )

        # Generar de forma asíncrona
        response = await model.generate_content_async(prompt, **kwargs)

        return response.text


class GeminiMedicoGeneral(GeminiClient):
    """Cliente Gemini especializado para el médico general"""

    def __init__(self):
        """Inicializa con configuración para médico general"""
        super().__init__(
            model_name=settings.gemini_pro_model,
            temperature=0.2  # Ligeramente más alta para razonamiento general
        )


class GeminiEspecialista(GeminiClient):
    """Cliente Gemini especializado para specialists"""

    def __init__(self):
        """Inicializa con configuración para specialists"""
        super().__init__(
            model_name=settings.gemini_pro_model,  # Pro para máxima calidad
            temperature=0.1  # Baja para precisión médica
        )


# Instancias globales
gemini_medico_general = GeminiMedicoGeneral()
gemini_especialista = GeminiEspecialista()
