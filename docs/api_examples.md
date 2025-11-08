# API Examples

Complete examples for using the Clinical Crew API.

## Table of Contents

- [Authentication](#authentication)
- [Create Consultation](#create-consultation)
- [Get Consultation Status](#get-consultation-status)
- [Get Complete Consultation](#get-complete-consultation)
- [Provide Additional Information](#provide-additional-information)
- [Example Use Cases](#example-use-cases)

## Base URL

```
Development: http://localhost:8000
Production: https://your-domain.com
```

## Authentication

Currently, the API does not require authentication. This will be implemented in future versions.

## Create Consultation

Create a new medical consultation that will be evaluated by the multi-agent system.

### Endpoint

```
POST /api/v1/consultation
```

### Request Body

```json
{
  "consultation": "Patient question or clinical case",
  "contexto": {
    "edad": 45,
    "sexo": "masculino",
    "diagnosticos": ["Diabetes Mellitus tipo 2", "Hipertensión arterial"],
    "medicamentos_actuales": ["Metformina 850mg c/12h", "Losartán 50mg c/24h"],
    "alergias": ["Penicilina"],
    "laboratorios": {
      "glucosa": "180 mg/dL",
      "hba1c": "8.5%",
      "creatinina": "1.2 mg/dL"
    },
    "signos_vitales": {
      "presion_arterial": "140/90 mmHg",
      "frecuencia_cardiaca": "78 lpm"
    }
  },
  "usuario_id": "optional-user-id"
}
```

### Response (201 Created)

```json
{
  "consulta_id": "507f1f77bcf86cd799439011",
  "estado": "completado",
  "mensaje": "Consultation completed successfully",
  "clinical_record": {
    "general_summary": "Summary from general practitioner...",
    "complete_notes": "Complete formatted clinical record...",
    "final_response": "Final integrated answer...",
    "management_plan": ["Step 1", "Step 2", "Step 3"],
    "recommended_followup": "Follow-up recommendations..."
  }
}
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/consultation" \
  -H "Content-Type: application/json" \
  -d '{
    "consultation": "Paciente con diabetes tipo 2 descompensada. ¿Puedo iniciar sertralina para depresión?",
    "contexto": {
      "edad": 45,
      "sexo": "masculino",
      "diagnosticos": ["Diabetes Mellitus tipo 2"],
      "medicamentos_actuales": ["Metformina 850mg c/12h", "Glibenclamida 5mg c/24h"],
      "alergias": []
    }
  }'
```

### Python Example

```python
import requests

url = "http://localhost:8000/api/v1/consultation"

data = {
    "consultation": "Paciente con diabetes tipo 2 descompensada. ¿Puedo iniciar sertralina para depresión?",
    "contexto": {
        "edad": 45,
        "sexo": "masculino",
        "diagnosticos": ["Diabetes Mellitus tipo 2"],
        "medicamentos_actuales": ["Metformina 850mg c/12h", "Glibenclamida 5mg c/24h"],
        "alergias": []
    }
}

response = requests.post(url, json=data)
print(response.json())
```

## Get Consultation Status

Check the current status of a consultation.

### Endpoint

```
GET /api/v1/consultation/{consulta_id}/estado
```

### Response

```json
{
  "consulta_id": "507f1f77bcf86cd799439011",
  "estado": "interconsultando",
  "created_at": "2025-11-08T10:30:00Z",
  "updated_at": "2025-11-08T10:31:00Z",
  "completed_at": null,
  "progress": {
    "evaluacion_completada": true,
    "interconsultas_generadas": 2,
    "contrarreferencias_recibidas": 1,
    "expediente_generado": false
  },
  "pending_questions": [],
  "error": null
}
```

### cURL Example

```bash
curl -X GET "http://localhost:8000/api/v1/consultation/507f1f77bcf86cd799439011/estado"
```

## Get Complete Consultation

Retrieve the complete consultation with all details.

### Endpoint

```
GET /api/v1/consultation/{consulta_id}
```

### Response

```json
{
  "consulta_id": "507f1f77bcf86cd799439011",
  "usuario_id": null,
  "original_consultation": "Paciente con diabetes tipo 2...",
  "patient_context": { ... },
  "estado": "completado",
  "timestamp": "2025-11-08T10:30:00Z",
  "general_evaluation": {
    "can_answer_directly": false,
    "required_specialists": ["Endocrinología", "Farmacología"],
    "razonamiento": "...",
    "estimated_complexity": 0.7
  },
  "interconsultations": [...],
  "counter_referrals": [...],
  "clinical_record": {...},
  "created_at": "2025-11-08T10:30:00Z",
  "updated_at": "2025-11-08T10:32:00Z"
}
```

## Provide Additional Information

If specialists request additional information, use this endpoint.

### Endpoint

```
POST /api/v1/consultation/{consulta_id}/responder
```

### Request Body

```json
{
  "additional_information": {
    "creatinina": "1.2 mg/dL",
    "hba1c": "8.5%",
    "presion_arterial": "140/90 mmHg"
  }
}
```

### Response

```json
{
  "consulta_id": "507f1f77bcf86cd799439011",
  "estado": "procesando",
  "mensaje": "Additional information received. Processing continues..."
}
```

## Example Use Cases

### Case 1: Simple Medical Question

**Scenario:** General medical question that doesn't require specialist consultation.

```bash
curl -X POST "http://localhost:8000/api/v1/consultation" \
  -H "Content-Type: application/json" \
  -d '{
    "consultation": "¿Cuáles son los signos de alerta de hipertensión arterial?",
    "contexto": {
      "edad": 55,
      "sexo": "femenino",
      "diagnosticos": [],
      "medicamentos_actuales": [],
      "alergias": []
    }
  }'
```

**Expected Result:** Direct answer from general practitioner without specialist consultation.

### Case 2: Complex Case Requiring Multiple Specialists

**Scenario:** Patient with diabetes, depression, and cardiovascular risk.

```bash
curl -X POST "http://localhost:8000/api/v1/consultation" \
  -H "Content-Type: application/json" \
  -d '{
    "consultation": "Paciente masculino de 55 años con DM2, HTA e historia familiar de cardiopatía isquémica. Presenta depresión mayor. ¿Cuál antidepresivo es más seguro considerando su perfil cardiovascular y metabólico?",
    "contexto": {
      "edad": 55,
      "sexo": "masculino",
      "diagnosticos": [
        "Diabetes Mellitus tipo 2",
        "Hipertensión arterial",
        "Depresión mayor"
      ],
      "medicamentos_actuales": [
        "Metformina 1000mg c/12h",
        "Enalapril 10mg c/12h",
        "Aspirina 100mg c/24h"
      ],
      "alergias": [],
      "antecedentes": {
        "familiares": "Padre con IAM a los 60 años"
      },
      "laboratorios": {
        "glucosa": "165 mg/dL",
        "hba1c": "7.8%",
        "colesterol_total": "220 mg/dL",
        "ldl": "140 mg/dL"
      }
    }
  }'
```

**Expected Result:** Consultation with Cardiology, Endocrinology, and Clinical Pharmacology specialists.

### Case 3: Drug Interaction Check

**Scenario:** Check for drug interactions before adding new medication.

```bash
curl -X POST "http://localhost:8000/api/v1/consultation" \
  -H "Content-Type: application/json" \
  -d '{
    "consultation": "¿Existen interacciones significativas si agrego amiodarona a este paciente?",
    "contexto": {
      "edad": 68,
      "sexo": "masculino",
      "diagnosticos": [
        "Fibrilación auricular",
        "Hipertensión arterial",
        "Hipotiroidismo"
      ],
      "medicamentos_actuales": [
        "Warfarina 5mg c/24h",
        "Atenolol 50mg c/12h",
        "Levotiroxina 100mcg c/24h"
      ],
      "alergias": []
    }
  }'
```

**Expected Result:** Pharmacology specialist analysis of drug interactions.

## Response Status Codes

| Code | Description                                 |
| ---- | ------------------------------------------- |
| 200  | OK - Request successful                     |
| 201  | Created - Consultation created successfully |
| 400  | Bad Request - Invalid input                 |
| 404  | Not Found - Consultation not found          |
| 500  | Internal Server Error - Server error        |

## Error Responses

```json
{
  "detail": "Error description here"
}
```

## Rate Limiting

Currently not implemented. Will be added in future versions.

## WebSocket Support

WebSocket support for real-time consultation updates is planned for future releases.

## Notes

- All timestamps are in UTC
- Patient context is flexible - include relevant information
- Specialist selection is automatic based on the consultation
- Multiple specialists can be consulted in parallel
- Evidence-based responses include citations
