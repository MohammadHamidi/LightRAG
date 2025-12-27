"""
Prompt Template Loader
Handles loading and rendering YAML-based prompt templates for entity extraction.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from .validator import PromptTemplateValidator


class PromptTemplateLoader:
    """
    Loads and manages YAML-based prompt templates.

    Supports:
    - Loading from template directory by name
    - Loading from custom file path
    - Template caching for performance
    - Variable substitution and rendering
    """

    def __init__(
        self,
        template_name: Optional[str] = None,
        template_dir: Optional[str] = None,
        custom_template_path: Optional[str] = None,
    ):
        """
        Initialize the template loader.

        Args:
            template_name: Name of template to load from template_dir (e.g., 'default')
            template_dir: Directory containing template YAML files
            custom_template_path: Direct path to a custom template file (overrides template_name)
        """
        self.template_name = template_name or "default"
        self.template_dir = template_dir or self._get_default_template_dir()
        self.custom_template_path = custom_template_path

        self._template_cache: Optional[Dict[str, Any]] = None
        self._validator = PromptTemplateValidator()

        # Load the template on initialization
        self._load_template()

    def _get_default_template_dir(self) -> str:
        """Get the default template directory path."""
        current_file = Path(__file__)
        return str(current_file.parent / "templates")

    def _load_template(self) -> None:
        """Load and validate the template from YAML file."""
        template_path = self._resolve_template_path()

        if not os.path.exists(template_path):
            raise FileNotFoundError(
                f"Template file not found: {template_path}"
            )

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(
                f"Failed to parse template YAML at {template_path}: {e}"
            )

        # Validate the template structure
        is_valid, errors = self._validator.validate(template_data)
        if not is_valid:
            error_msg = "\n".join(errors)
            raise ValueError(
                f"Template validation failed for {template_path}:\n{error_msg}"
            )

        self._template_cache = template_data

    def _resolve_template_path(self) -> str:
        """Resolve the full path to the template file."""
        if self.custom_template_path:
            return self.custom_template_path

        # Construct path from template_dir and template_name
        return os.path.join(self.template_dir, f"{self.template_name}.yaml")

    def reload(self) -> None:
        """Reload the template from disk (useful for development/testing)."""
        self._template_cache = None
        self._load_template()

    def get_metadata(self) -> Dict[str, Any]:
        """Get template metadata."""
        if not self._template_cache:
            raise RuntimeError("Template not loaded")

        return self._template_cache.get("template_metadata", {})

    def get_entity_types(self) -> list[str]:
        """Get entity types defined in the template."""
        metadata = self.get_metadata()
        return metadata.get("entity_types", [])

    def get_delimiters(self) -> Dict[str, str]:
        """Get delimiter configuration."""
        if not self._template_cache:
            raise RuntimeError("Template not loaded")

        return self._template_cache.get("delimiters", {
            "tuple_delimiter": "<|#|>",
            "completion_delimiter": "<|COMPLETE|>",
            "record_delimiter": "##"
        })

    def get_extraction_settings(self) -> Dict[str, Any]:
        """Get extraction-specific settings."""
        if not self._template_cache:
            raise RuntimeError("Template not loaded")

        return self._template_cache.get("extraction_settings", {})

    def get_examples(self) -> list[str]:
        """Get extraction examples."""
        if not self._template_cache:
            raise RuntimeError("Template not loaded")

        examples_data = self._template_cache.get("examples", {}).get("entity_extraction", [])

        # Format examples into string format
        formatted_examples = []
        for example in examples_data:
            if isinstance(example, dict):
                # Handle dict format with input/output
                example_str = f"<Entity_types>\n[{', '.join(self.get_entity_types())}]\n\n"
                example_str += f"<Input Text>\n```\n{example.get('input', '')}\n```\n\n"
                example_str += f"<Output>\n{example.get('output', '')}\n"
                formatted_examples.append(example_str)
            elif isinstance(example, str):
                # Handle pre-formatted string examples
                formatted_examples.append(example)

        return formatted_examples

    def render_prompt(self, prompt_key: str, **variables) -> str:
        """
        Render a prompt template with variable substitution.

        Args:
            prompt_key: Key identifying the prompt (e.g., 'entity_extraction_system')
            **variables: Variables to substitute in the template

        Returns:
            Rendered prompt string
        """
        if not self._template_cache:
            raise RuntimeError("Template not loaded")

        prompts = self._template_cache.get("prompts", {})

        if prompt_key not in prompts:
            raise KeyError(
                f"Prompt '{prompt_key}' not found in template. "
                f"Available prompts: {list(prompts.keys())}"
            )

        prompt_config = prompts[prompt_key]

        # Build the full prompt from sections
        prompt_parts = []

        if "role" in prompt_config:
            prompt_parts.append(prompt_config["role"])

        if "instructions" in prompt_config:
            prompt_parts.append(prompt_config["instructions"])

        if "format_example" in prompt_config:
            prompt_parts.append(prompt_config["format_example"])

        if "task_description" in prompt_config:
            prompt_parts.append(prompt_config["task_description"])

        if "input_template" in prompt_config:
            prompt_parts.append(prompt_config["input_template"])

        if "instruction" in prompt_config:
            prompt_parts.append(prompt_config["instruction"])

        prompt_template = "\n\n".join(prompt_parts)

        # Add examples if this is the system prompt
        if prompt_key == "entity_extraction_system" and "examples" in variables:
            # Examples are already formatted, just insert
            prompt_template = prompt_template.replace("{examples}", "{examples}")

        # Perform variable substitution
        try:
            rendered = prompt_template.format(**variables)
        except KeyError as e:
            missing_var = str(e).strip("'")
            raise ValueError(
                f"Missing required variable '{missing_var}' for prompt '{prompt_key}'. "
                f"Required variables: {prompt_config.get('variables', [])}"
            )

        return rendered

    def get_prompt(self, prompt_key: str, **variables) -> str:
        """Alias for render_prompt for backward compatibility."""
        return self.render_prompt(prompt_key, **variables)

    def get_all_prompt_keys(self) -> list[str]:
        """Get list of all available prompt keys in the template."""
        if not self._template_cache:
            raise RuntimeError("Template not loaded")

        return list(self._template_cache.get("prompts", {}).keys())

    def to_dict(self) -> Dict[str, Any]:
        """Export the full template as a dictionary."""
        if not self._template_cache:
            raise RuntimeError("Template not loaded")

        return self._template_cache.copy()


def load_template(
    template_name: Optional[str] = None,
    template_dir: Optional[str] = None,
    custom_template_path: Optional[str] = None,
) -> PromptTemplateLoader:
    """
    Convenience function to load a template.

    Args:
        template_name: Name of template (e.g., 'default', 'scientific')
        template_dir: Directory containing templates
        custom_template_path: Path to custom template file

    Returns:
        PromptTemplateLoader instance
    """
    return PromptTemplateLoader(
        template_name=template_name,
        template_dir=template_dir,
        custom_template_path=custom_template_path,
    )
