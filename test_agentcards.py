#!/usr/bin/env python3
"""
Test script for Agent Card implementation.

This script verifies that Agent Cards are correctly loaded and accessible.
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.agentcard_loader import (
    agentcard_registry,
    get_agent_card,
    get_agent_llm_config,
    initialize_agentcards
)


def test_agentcard_loading():
    """Test loading all Agent Cards"""
    print("=" * 60)
    print("Agent Card Loading Test")
    print("=" * 60)

    try:
        initialize_agentcards()
        print("\n✅ Agent Cards loaded successfully")
    except Exception as e:
        print(f"\n❌ Error loading Agent Cards: {str(e)}")
        return False

    return True


def test_agentcard_access():
    """Test accessing Agent Cards"""
    print("\n" + "=" * 60)
    print("Agent Card Access Test")
    print("=" * 60)

    agents = ["general_practitioner", "cardiology", "endocrinology", "pharmacology"]

    for agent_name in agents:
        print(f"\n--- Testing: {agent_name} ---")

        # Test get_agent_card
        card = get_agent_card(agent_name)
        if card:
            print(f"  ✓ Agent Card loaded")
        else:
            print(f"  ✗ Agent Card not found")

        # Test get_agent_llm_config
        llm_config = get_agent_llm_config(agent_name)
        if llm_config:
            print(f"  ✓ LLM Config: {llm_config.get('model_name', 'Unknown')} @ T={llm_config.get('temperature', 'Unknown')}")
        else:
            print(f"  ✗ LLM Config not found")

        # Test metadata access
        metadata = agentcard_registry.get_agent_metadata(agent_name)
        if metadata:
            print(f"  ✓ Metadata: v{metadata.get('version', 'Unknown')} by {metadata.get('owner', 'Unknown')}")
        else:
            print(f"  ✗ Metadata not found")

        # Test tools access
        tools = agentcard_registry.get_agent_tools(agent_name)
        if tools:
            print(f"  ✓ Tools: {len(tools)} configured")
        else:
            print(f"  ✗ Tools not found")

        # Test risks access
        risks = agentcard_registry.get_agent_risks(agent_name)
        if risks:
            print(f"  ✓ Risks: {len(risks)} identified")
        else:
            print(f"  ✗ Risks not found")


def test_agent_initialization():
    """Test agent initialization with Agent Cards"""
    print("\n" + "=" * 60)
    print("Agent Initialization Test")
    print("=" * 60)

    try:
        # Test General Practitioner
        print("\n--- General Practitioner ---")
        from app.agents.general_practitioner import general_practitioner
        if hasattr(general_practitioner, 'agent_card'):
            print("  ✓ GP has agent_card attribute")
        if hasattr(general_practitioner, 'llm_config'):
            print("  ✓ GP has llm_config attribute")

        # Test Specialist
        print("\n--- Specialist (Cardiology) ---")
        from app.agents.specialists import get_specialist_agent
        cardiology_agent = get_specialist_agent("cardiology")
        if hasattr(cardiology_agent, 'agent_card'):
            print("  ✓ Cardiology agent has agent_card attribute")
        if hasattr(cardiology_agent, 'llm_config'):
            print("  ✓ Cardiology agent has llm_config attribute")

        print("\n✅ Agent initialization with Agent Cards successful")
        return True

    except Exception as e:
        print(f"\n❌ Error in agent initialization: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_export_summaries():
    """Test exporting Agent Card summaries"""
    print("\n" + "=" * 60)
    print("Agent Card Summary Export Test")
    print("=" * 60)

    agents = ["general_practitioner", "cardiology"]

    for agent_name in agents:
        summary = agentcard_registry.export_card_summary(agent_name)
        if summary:
            print(f"\n{summary}")
        else:
            print(f"\n✗ Could not export summary for {agent_name}")


def main():
    """Run all tests"""
    print("\n🧪 Starting Agent Card Tests...\n")

    # Test 1: Loading
    if not test_agentcard_loading():
        print("\n❌ Loading test failed. Stopping.")
        return

    # Test 2: Access
    test_agentcard_access()

    # Test 3: Agent Initialization
    test_agent_initialization()

    # Test 4: Export Summaries
    test_export_summaries()

    print("\n" + "=" * 60)
    print("✅ All Agent Card tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
