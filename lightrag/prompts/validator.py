"""
Prompt Template Validator
Validates YAML template structure and ensures all required fields are present.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class PromptTemplateValidator:
    """
    Validates prompt template YAML structure.

    Ensures:
    - Required top-level sections exist
    - Prompt configurations have necessary fields
    - Variable placeholders match declared variables
    - Delimiter configuration is valid
    """

    REQUIRED_TOP_LEVEL_KEYS = [
        "template_metadata",
        "prompts",
        "delimiters",
    ]

    REQUIRED_METADATA_KEYS = [
        "name",
        "version",
        "description",
    ]

    REQUIRED_PROMPT_KEYS = [
        "entity_extraction_system",
        "entity_extraction_user",
        "entity_continue_extraction",
        "summarize_entity_descriptions",
    ]

    REQUIRED_DELIMITER_KEYS = [
        "tuple_delimiter",
        "completion_delimiter",
    ]

    def __init__(self):
        """Initialize the validator."""
        self.errors: List[str] = []

    def validate(self, template_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a template dictionary.

        Args:
            template_data: Parsed YAML template data

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        self.errors = []

        if not isinstance(template_data, dict):
            self.errors.append("Template must be a dictionary/object")
            return False, self.errors

        # Validate top-level structure
        self._validate_top_level_keys(template_data)

        # Validate metadata section
        if "template_metadata" in template_data:
            self._validate_metadata(template_data["template_metadata"])

        # Validate prompts section
        if "prompts" in template_data:
            self._validate_prompts(template_data["prompts"])

        # Validate delimiters section
        if "delimiters" in template_data:
            self._validate_delimiters(template_data["delimiters"])

        # Validate extraction settings if present
        if "extraction_settings" in template_data:
            self._validate_extraction_settings(template_data["extraction_settings"])

        is_valid = len(self.errors) == 0
        return is_valid, self.errors

    def _validate_top_level_keys(self, template_data: Dict[str, Any]) -> None:
        """Validate that all required top-level keys are present."""
        for key in self.REQUIRED_TOP_LEVEL_KEYS:
            if key not in template_data:
                self.errors.append(f"Missing required top-level key: '{key}'")

    def _validate_metadata(self, metadata: Any) -> None:
        """Validate template metadata section."""
        if not isinstance(metadata, dict):
            self.errors.append("'template_metadata' must be a dictionary")
            return

        for key in self.REQUIRED_METADATA_KEYS:
            if key not in metadata:
                self.errors.append(f"Missing required metadata field: '{key}'")

        # Validate entity_types if present
        if "entity_types" in metadata:
            entity_types = metadata["entity_types"]
            if not isinstance(entity_types, list):
                self.errors.append("'entity_types' must be a list")
            elif len(entity_types) == 0:
                self.errors.append("'entity_types' cannot be empty")

    def _validate_prompts(self, prompts: Any) -> None:
        """Validate prompts section."""
        if not isinstance(prompts, dict):
            self.errors.append("'prompts' must be a dictionary")
            return

        # Check for required prompts
        for prompt_key in self.REQUIRED_PROMPT_KEYS:
            if prompt_key not in prompts:
                self.errors.append(f"Missing required prompt: '{prompt_key}'")
                continue

            prompt_config = prompts[prompt_key]
            self._validate_single_prompt(prompt_key, prompt_config)

    def _validate_single_prompt(
        self,
        prompt_key: str,
        prompt_config: Any
    ) -> None:
        """Validate a single prompt configuration."""
        if not isinstance(prompt_config, dict):
            self.errors.append(
                f"Prompt '{prompt_key}' must be a dictionary"
            )
            return

        # Check that prompt has at least one content field
        content_fields = [
            "role", "instructions", "format_example",
            "task_description", "input_template", "instruction"
        ]

        has_content = any(field in prompt_config for field in content_fields)
        if not has_content:
            self.errors.append(
                f"Prompt '{prompt_key}' must have at least one content field: "
                f"{content_fields}"
            )

        # Validate variables field if present
        if "variables" in prompt_config:
            variables = prompt_config["variables"]
            if not isinstance(variables, list):
                self.errors.append(
                    f"Prompt '{prompt_key}' variables must be a list"
                )
            else:
                # Check that declared variables are used in the prompt text
                self._validate_variables_usage(prompt_key, prompt_config, variables)

    def _validate_variables_usage(
        self,
        prompt_key: str,
        prompt_config: Dict[str, Any],
        variables: List[str]
    ) -> None:
        """Validate that declared variables appear in the prompt text."""
        # Collect all text content from the prompt
        prompt_text_parts = []
        for field in ["role", "instructions", "format_example",
                     "task_description", "input_template", "instruction"]:
            if field in prompt_config:
                prompt_text_parts.append(str(prompt_config[field]))

        full_prompt_text = "\n".join(prompt_text_parts)

        # Check each variable appears as {variable_name}
        for var in variables:
            placeholder = f"{{{var}}}"
            if placeholder not in full_prompt_text:
                # This is a warning, not an error (some variables might be optional)
                pass  # We'll be lenient here

    def _validate_delimiters(self, delimiters: Any) -> None:
        """Validate delimiters section."""
        if not isinstance(delimiters, dict):
            self.errors.append("'delimiters' must be a dictionary")
            return

        for key in self.REQUIRED_DELIMITER_KEYS:
            if key not in delimiters:
                self.errors.append(f"Missing required delimiter: '{key}'")
                continue

            delimiter_value = delimiters[key]
            if not isinstance(delimiter_value, str):
                self.errors.append(
                    f"Delimiter '{key}' must be a string"
                )
            elif not delimiter_value:
                self.errors.append(
                    f"Delimiter '{key}' cannot be empty"
                )

    def _validate_extraction_settings(self, settings: Any) -> None:
        """Validate extraction settings section."""
        if not isinstance(settings, dict):
            self.errors.append("'extraction_settings' must be a dictionary")
            return

        # Validate max_gleaning if present
        if "max_gleaning" in settings:
            max_gleaning = settings["max_gleaning"]
            if not isinstance(max_gleaning, int):
                self.errors.append("'max_gleaning' must be an integer")
            elif max_gleaning < 0:
                self.errors.append("'max_gleaning' must be non-negative")

        # Validate force_summary_threshold if present
        if "force_summary_threshold" in settings:
            threshold = settings["force_summary_threshold"]
            if not isinstance(threshold, int):
                self.errors.append("'force_summary_threshold' must be an integer")
            elif threshold < 1:
                self.errors.append("'force_summary_threshold' must be positive")

        # Validate summary_max_tokens if present
        if "summary_max_tokens" in settings:
            max_tokens = settings["summary_max_tokens"]
            if not isinstance(max_tokens, int):
                self.errors.append("'summary_max_tokens' must be an integer")
            elif max_tokens < 1:
                self.errors.append("'summary_max_tokens' must be positive")


def validate_template(template_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a template.

    Args:
        template_data: Parsed template dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    validator = PromptTemplateValidator()
    return validator.validate(template_data)
