"""
Example usage of the Clinical Crew API.

This script demonstrates how to interact with the medical consultation system.
"""

import requests
import json
import time
from typing import Dict, Any


API_BASE_URL = "http://localhost:8000"


def create_consultation(consultation: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new medical consultation.

    Args:
        consultation: Medical question or case
        context: Patient context

    Returns:
        API response
    """
    url = f"{API_BASE_URL}/api/v1/consultation"

    payload = {"consultation": consultation, "context": context}

    print(f"🏥 Creating consultation...")
    print(f"Question: {consultation}\n")

    response = requests.post(url, json=payload)
    response.raise_for_status()

    return response.json()


def get_consultation_status(consultation_id: str) -> Dict[str, Any]:
    """
    Get consultation status.

    Args:
        consultation_id: Consultation ID

    Returns:
        Status information
    """
    url = f"{API_BASE_URL}/api/v1/consultation/{consultation_id}/status"

    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def get_consultation(consultation_id: str) -> Dict[str, Any]:
    """
    Get complete consultation.

    Args:
        consultation_id: Consultation ID

    Returns:
        Complete consultation data
    """
    url = f"{API_BASE_URL}/api/v1/consultation/{consultation_id}"

    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def print_response(response: Dict[str, Any]):
    """Print formatted response."""
    print("\n" + "=" * 80)
    print("CONSULTATION RESPONSE")
    print("=" * 80)

    print(f"\nConsultation ID: {response.get('consultation_id')}")
    print(f"Status: {response.get('status')}")

    if response.get("message"):
        print(f"Message: {response.get('message')}")

    if response.get("clinical_record"):
        record = response["clinical_record"]

        print("\n" + "-" * 80)
        print("FINAL ANSWER")
        print("-" * 80)
        print(record.get("final_response", ""))

        if record.get("management_plan"):
            print("\n" + "-" * 80)
            print("MANAGEMENT PLAN")
            print("-" * 80)
            for i, step in enumerate(record["management_plan"], 1):
                print(f"{i}. {step}")

        if record.get("complete_notes"):
            print("\n" + "-" * 80)
            print("COMPLETE CLINICAL RECORD")
            print("-" * 80)
            print(record["complete_notes"])

    if response.get("progress"):
        print("\n" + "-" * 80)
        print("PROGRESS")
        print("-" * 80)
        progress = response["progress"]
        print(json.dumps(progress, indent=2))


# Example 1: Simple medical question
def example_simple_question():
    """Example of a simple medical question."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Simple Medical Question")
    print("=" * 80)

    consultation = "What are the warning signs of arterial hypertension?"

    context = {
        "age": 55,
        "sex": "female",
        "diagnoses": [],
        "current_medications": [],
        "allergies": [],
    }

    response = create_consultation(consultation, context)
    print_response(response)


# Example 2: Complex case requiring specialists
def example_complex_case():
    """Example of a complex case requiring multiple specialists."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Complex Multi-Specialist Consultation")
    print("=" * 80)

    consultation = (
        "Male patient, 45 years old, with decompensated type 2 diabetes. "
        "Can I start sertraline for depression? Patient is currently on "
        "metformin and glibenclamide."
    )

    context = {
        "age": 45,
        "sex": "male",
        "diagnoses": ["Type 2 Diabetes Mellitus", "Depression"],
        "current_medications": [
            "Metformin 850mg every 12 hours",
            "Glibenclamide 5mg every 24 hours",
        ],
        "allergies": [],
        "laboratory_results": {
            "glucose": "180 mg/dL",
            "hba1c": "8.5%",
            "creatinine": "1.2 mg/dL",
        },
    }

    response = create_consultation(consultation, context)
    print_response(response)


# Example 3: Drug interaction check
def example_drug_interaction():
    """Example of drug interaction consultation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Drug Interaction Check")
    print("=" * 80)

    consultation = (
        "Are there significant interactions if I add amiodarone to this patient?"
    )

    context = {
        "age": 68,
        "sex": "male",
        "diagnoses": ["Atrial fibrillation", "Arterial hypertension", "Hypothyroidism"],
        "current_medications": [
            "Warfarin 5mg every 24 hours",
            "Atenolol 50mg every 12 hours",
            "Levothyroxine 100mcg every 24 hours",
        ],
        "allergies": [],
    }

    response = create_consultation(consultation, context)
    print_response(response)


# Example 4: Monitor consultation progress
def example_monitor_progress():
    """Example of monitoring consultation progress."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Monitor Consultation Progress")
    print("=" * 80)

    # Create consultation
    consultation = "Patient with diabetes and hypertension. Best antidepressant option?"

    context = {
        "age": 50,
        "sex": "male",
        "diagnoses": ["Type 2 Diabetes", "Hypertension"],
        "current_medications": ["Metformin 1000mg", "Losartan 50mg"],
        "allergies": [],
    }

    response = create_consultation(consultation, context)
    consultation_id = response["consultation_id"]

    # Monitor progress
    print(f"\nMonitoring consultation {consultation_id}...\n")

    for i in range(5):
        time.sleep(2)  # Wait 2 seconds

        status = get_consultation_status(consultation_id)

        print(f"[{i+1}] Status: {status['status']}")
        print(f"    Progress: {status['progress']}")

        if status["status"] in ["completed", "error"]:
            break

    # Get final result
    if status["status"] == "completed":
        print("\n✓ Consultation completed!")
        final = get_consultation(consultation_id)
        print_response(final)


def check_server_health():
    """Check if the server is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        response.raise_for_status()

        print("✓ Server is healthy")
        print(f"  Service: {response.json().get('service')}")
        print(f"  Version: {response.json().get('version')}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ Server is not responding: {e}")
        print(f"\nMake sure the server is running:")
        print(f"  python -m app.main")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("Clinical Crew - EXAMPLE USAGE")
    print("=" * 80)

    # Check server health
    if not check_server_health():
        exit(1)

    # Run examples
    try:
        # Uncomment the examples you want to run

        example_simple_question()
        # example_complex_case()
        # example_drug_interaction()
        # example_monitor_progress()

        print("\n" + "=" * 80)
        print("EXAMPLES COMPLETED")
        print("=" * 80)

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Error: {e}")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
