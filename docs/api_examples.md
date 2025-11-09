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
  "context": {
    "age": 45,
    "sex": "male",
    "diagnoses": ["Type 2 Diabetes Mellitus", "Hypertension"],
    "current_medications": ["Metformin 850mg q12h", "Losartan 50mg q24h"],
    "allergies": ["Penicillin"],
    "lab_results": {
      "glucose": "180 mg/dL",
      "hba1c": "8.5%",
      "creatinine": "1.2 mg/dL"
    },
    "vital_signs": {
      "blood_pressure": "140/90 mmHg",
      "heart_rate": "78 bpm"
    }
  },
  "user_id": "optional-user-id"
}
```

### Response (201 Created)

```json
{
  "consultation_id": "507f1f77bcf86cd799439011",
  "status": "completed",
  "message": "Consultation completed successfully",
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
    "consultation": "Patient with decompensated type 2 diabetes. Can I start sertraline for depression?",
    "context": {
      "age": 45,
      "sex": "male",
      "diagnoses": ["Type 2 Diabetes Mellitus"],
      "current_medications": ["Metformin 850mg q12h", "Glibenclamide 5mg q24h"],
      "allergies": []
    }
  }'
```

### Python Example

```python
import requests

url = "http://localhost:8000/api/v1/consultation"

data = {
    "consultation": "Patient with decompensated type 2 diabetes. Can I start sertraline for depression?",
    "context": {
        "age": 45,
        "sex": "male",
        "diagnoses": ["Type 2 Diabetes Mellitus"],
        "current_medications": ["Metformin 850mg q12h", "Glibenclamide 5mg q24h"],
        "allergies": []
    }
}

response = requests.post(url, json=data)
print(response.json())
```

## Get Consultation Status

Check the current status of a consultation.

### Endpoint

```
GET /api/v1/consultation/{consultation_id}/status
```

### Response

```json
{
  "consultation_id": "507f1f77bcf86cd799439011",
  "status": "interconsulting",
  "created_at": "2025-11-08T10:30:00Z",
  "updated_at": "2025-11-08T10:31:00Z",
  "completed_at": null,
  "progress": {
    "interrogation_completed": true,
    "evaluation_completed": true,
    "interconsultations_generated": 2,
    "counter_referrals_received": 1,
    "clinical_record_generated": false
  },
  "error": null
}
```

### cURL Example

```bash
curl -X GET "http://localhost:8000/api/v1/consultation/507f1f77bcf86cd799439011/status"
```

## Get Complete Consultation

Retrieve the complete consultation with all details.

### Endpoint

```
GET /api/v1/consultation/{consultation_id}
```

### Response

```json
{
  "consultation_id": "507f1f77bcf86cd799439011",
  "user_id": null,
  "original_consultation": "Patient with type 2 diabetes...",
  "patient_context": { ... },
  "status": "completed",
  "timestamp": "2025-11-08T10:30:00Z",
  "interrogation_questions": [],
  "interrogation_completed": true,
  "general_evaluation": {
    "can_answer_directly": false,
    "required_specialists": ["Endocrinology", "Pharmacology"],
    "reasoning": "...",
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

If the GP requests additional patient information during interrogation, use this endpoint.

### Endpoint

```
POST /api/v1/consultation/{consultation_id}/respond
```

### Request Body

```json
{
  "responses": {
    "question_id_1": "answer_value_1",
    "question_id_2": "answer_value_2"
  }
}
```

### Response

```json
{
  "consultation_id": "507f1f77bcf86cd799439011",
  "status": "processing",
  "message": "Responses received. Processing continues..."
}
```

## Example Use Cases

### Case 1: Simple Medical Question

**Scenario:** General medical question that doesn't require specialist consultation.

```bash
curl -X POST "http://localhost:8000/api/v1/consultation" \
  -H "Content-Type: application/json" \
  -d '{
    "consultation": "What are the warning signs of hypertension?",
    "context": {
      "age": 55,
      "sex": "female",
      "diagnoses": [],
      "current_medications": [],
      "allergies": []
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
    "consultation": "55-year-old male patient with type 2 diabetes, hypertension, and family history of ischemic heart disease. Presents with major depression. Which antidepressant is safest considering his cardiovascular and metabolic profile?",
    "context": {
      "age": 55,
      "sex": "male",
      "diagnoses": [
        "Type 2 Diabetes Mellitus",
        "Hypertension",
        "Major Depression"
      ],
      "current_medications": [
        "Metformin 1000mg q12h",
        "Enalapril 10mg q12h",
        "Aspirin 100mg q24h"
      ],
      "allergies": [],
      "medical_history": {
        "family": "Father with MI at age 60"
      },
      "lab_results": {
        "glucose": "165 mg/dL",
        "hba1c": "7.8%",
        "total_cholesterol": "220 mg/dL",
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
    "consultation": "Are there significant interactions if I add amiodarone to this patient?",
    "context": {
      "age": 68,
      "sex": "male",
      "diagnoses": [
        "Atrial fibrillation",
        "Hypertension",
        "Hypothyroidism"
      ],
      "current_medications": [
        "Warfarin 5mg q24h",
        "Atenolol 50mg q12h",
        "Levothyroxine 100mcg q24h"
      ],
      "allergies": []
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
