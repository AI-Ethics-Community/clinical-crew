"""
Agent Card loader and validator for Clinical Crew agents.

This module provides functionality to load, validate, and access Agent Cards
for all agents in the Clinical Crew system.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field

from app.config.settings import settings


class AgentCardRegistry:
    """
    Registry for Agent Cards used in the Clinical Crew system.

    This class provides a centralized way to load and access Agent Cards
    for all agents (General Practitioner and Specialists).
    """

    def __init__(self, agentcards_dir: Optional[Path] = None):
        """
        Initialize the Agent Card registry.

        Args:
            agentcards_dir: Directory containing Agent Card YAML files.
                          Defaults to app/config/agentcards/
        """
        if agentcards_dir is None:
            agentcards_dir = Path(__file__).parent.parent / "config" / "agentcards"

        self.agentcards_dir = agentcards_dir
        self._raw_data: Dict[str, Dict[str, Any]] = {}

    def load_all_cards(self) -> None:
        """
        Load all Agent Cards from the agentcards directory.

        Raises:
            FileNotFoundError: If agentcards directory does not exist
            ValueError: If any Agent Card fails validation
        """
        if not self.agentcards_dir.exists():
            raise FileNotFoundError(f"Agent cards directory not found: {self.agentcards_dir}")

        # Find all YAML files in agentcards directory
        yaml_files = list(self.agentcards_dir.glob("*.yaml")) + list(self.agentcards_dir.glob("*.yml"))

        if not yaml_files:
            print(f"Warning: No Agent Card YAML files found in {self.agentcards_dir}")
            return

        for yaml_file in yaml_files:
            agent_name = yaml_file.stem
            try:
                self.load_card(agent_name)
                print(f"✓ Loaded Agent Card: {agent_name}")
            except Exception as e:
                print(f"✗ Error loading Agent Card '{agent_name}': {str(e)}")
                raise

    def load_card(self, agent_name: str) -> Dict[str, Any]:
        """
        Load a specific Agent Card.

        Args:
            agent_name: Name of the agent (e.g., 'general_practitioner', 'cardiology')

        Returns:
            Loaded Agent Card data

        Raises:
            FileNotFoundError: If Agent Card file does not exist
        """
        yaml_path = self.agentcards_dir / f"{agent_name}.yaml"

        if not yaml_path.exists():
            # Try .yml extension
            yaml_path = self.agentcards_dir / f"{agent_name}.yml"

        if not yaml_path.exists():
            raise FileNotFoundError(f"Agent Card not found: {agent_name}")

        # Load raw YAML data
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self._raw_data[agent_name] = data

        return data

    def get_card(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a loaded Agent Card.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent Card data dictionary or None if not loaded
        """
        return self._raw_data.get(agent_name)

    def get_raw_data(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get raw YAML data for an Agent Card.

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary with raw Agent Card data or None if not loaded
        """
        return self._raw_data.get(agent_name)

    def list_loaded_cards(self) -> list[str]:
        """
        Get list of all loaded Agent Card names.

        Returns:
            List of agent names
        """
        return list(self._raw_data.keys())

    def get_agent_metadata(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata section from an Agent Card.

        Args:
            agent_name: Name of the agent

        Returns:
            Metadata dictionary or None if card not loaded
        """
        data = self.get_raw_data(agent_name)
        if data:
            return data.get('meta')
        return None

    def get_agent_tools(self, agent_name: str) -> Optional[list]:
        """
        Get tools/functions section from an Agent Card.

        Args:
            agent_name: Name of the agent

        Returns:
            List of tools or None if card not loaded
        """
        data = self.get_raw_data(agent_name)
        if data:
            return data.get('tools_functions', [])
        return None

    def get_agent_risks(self, agent_name: str) -> Optional[list]:
        """
        Get risks section from an Agent Card.

        Args:
            agent_name: Name of the agent

        Returns:
            List of risks or None if card not loaded
        """
        data = self.get_raw_data(agent_name)
        if data:
            return data.get('risks', [])
        return None

    def get_llm_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Extract LLM configuration from Agent Card.

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary with LLM configuration (model, version, temperature, etc.)
            Returns empty dict if agent card not found
        """
        data = self.get_raw_data(agent_name)
        if not data:
            return {}

        llm_config = {}

        # Extract from versioning section
        versioning = data.get('versioning', {})
        llm_config['model_version'] = versioning.get('model_version')
        llm_config['temperature'] = versioning.get('temperature')

        # Extract from tools section (gemini client)
        tools = data.get('tools_functions', [])
        for tool in tools:
            if 'gemini' in tool.get('name', '').lower():
                llm_config['model_name'] = tool.get('model')
                llm_config['purpose'] = tool.get('purpose')
                llm_config['scope'] = tool.get('scope')
                if 'temperature' in tool:
                    llm_config['temperature'] = tool.get('temperature')
                break

        return llm_config

    def export_card_summary(self, agent_name: str) -> Optional[str]:
        """
        Export a human-readable summary of an Agent Card.

        Args:
            agent_name: Name of the agent

        Returns:
            Formatted string summary or None if card not loaded
        """
        data = self.get_raw_data(agent_name)
        if not data:
            return None

        meta = data.get('meta', {})
        purpose = data.get('purpose', {})

        summary = f"""
Agent Card Summary: {meta.get('name', 'Unknown')}
{'=' * 60}

Version: {meta.get('version', 'Unknown')}
Owner: {meta.get('owner', 'Unknown')}
Last Updated: {meta.get('last_updated', 'Unknown')}

Purpose:
  {purpose.get('objective', 'No objective specified')}

Roles: {', '.join(data.get('agent_role', []))}

LLM Configuration:
  Model: {self.get_llm_config(agent_name).get('model_name', 'Unknown')}
  Temperature: {self.get_llm_config(agent_name).get('temperature', 'Unknown')}

Tools: {len(data.get('tools_functions', []))} configured
Risks: {len(data.get('risks', []))} identified

Agent Card Standard:
  Citation: {data.get('agentcard_standard', {}).get('citation', 'Unknown')}
  Repository: {data.get('agentcard_standard', {}).get('repository', 'Unknown')}
"""
        return summary

    def validate_all_cards(self) -> Dict[str, bool]:
        """
        Validate all loaded Agent Cards.

        Returns:
            Dictionary mapping agent names to validation status (True = valid)
        """
        results = {}
        for agent_name in self.list_loaded_cards():
            try:
                card = self.get_card(agent_name)
                # Basic validation: check for required fields
                required_fields = ['agentcard', 'meta', 'purpose', 'agent_name']
                is_valid = card is not None and all(field in card for field in required_fields)
                results[agent_name] = is_valid
            except Exception as e:
                print(f"Validation failed for {agent_name}: {str(e)}")
                results[agent_name] = False

        return results


# Global registry instance
agentcard_registry = AgentCardRegistry()


def initialize_agentcards() -> None:
    """
    Initialize Agent Card registry by loading all cards.

    This function should be called during application startup.
    """
    try:
        agentcard_registry.load_all_cards()

        # Validate all cards
        validation_results = agentcard_registry.validate_all_cards()

        valid_count = sum(1 for v in validation_results.values() if v)
        total_count = len(validation_results)

        print(f"\nAgent Cards loaded: {valid_count}/{total_count} valid")

        # Print summaries
        for agent_name in agentcard_registry.list_loaded_cards():
            print(f"\n{agentcard_registry.export_card_summary(agent_name)}")

    except Exception as e:
        print(f"Error initializing Agent Cards: {str(e)}")
        raise


def get_agent_card(agent_name: str) -> Optional[Dict[str, Any]]:
    """
    Get an Agent Card for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., 'general_practitioner', 'cardiology')

    Returns:
        Agent Card data dictionary or None if not found
    """
    return agentcard_registry.get_card(agent_name)


def get_agent_llm_config(agent_name: str) -> Dict[str, Any]:
    """
    Get LLM configuration for a specific agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Dictionary with LLM configuration (empty dict if not found)
    """
    return agentcard_registry.get_llm_config(agent_name)
