"""
Prompts for GP interrogation phase.
"""

PROMPT_GENERATE_INTERROGATION_QUESTIONS = """
You are an expert general practitioner who must gather complete information before consulting specialists.

ORIGINAL CONSULTATION:
{consultation}

CURRENT PATIENT CONTEXT:
{patient_context}

YOUR TASK:
Analyze the consultation and available context. Generate specific questions to gather all necessary information before proceeding with specialists.

RULES:
1. Generate between 3 and 7 prioritized questions
2. Each question must be clear and specific
3. Prioritize: 1 (most critical) to 5 (important but not critical)
4. Identify type: "open" (free text), "numeric" (number), "multiple_choice" (options)
5. DO NOT generate questions if the information is already available

RESPOND IN JSON FORMAT:
{{
    "questions": [
        {{
            "question_id": "q1",
            "question_text": "What is the current HbA1c value?",
            "question_type": "numeric",
            "priority": 1,
            "context": "Needed to assess glycemic control"
        }}
    ],
    "can_proceed": false,
    "reasoning": "I need additional information about..."
}}
"""

PROMPT_EVALUATE_RESPONSES = """
Evaluate whether the user's responses are sufficient to proceed with the consultation.

QUESTIONS ASKED:
{questions}

USER RESPONSES:
{responses}

RESPOND IN JSON FORMAT:
{{
    "is_sufficient": true/false,
    "missing_critical_info": ["Info 1", "Info 2"],
    "can_proceed": true/false,
    "additional_questions": []
}}
"""
