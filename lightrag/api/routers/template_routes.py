"""
Template Management API Routes

Provides endpoints for managing and inspecting prompt templates.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
from pathlib import Path

from lightrag import LightRAG
from lightrag.api.routers.graph_routes import get_lightrag_instance

router = APIRouter(prefix="/templates", tags=["templates"])


# Response Models
# ---------------

class TemplateMetadata(BaseModel):
    """Metadata about a template."""
    name: str = Field(..., description="Template name")
    version: str = Field(..., description="Template version")
    description: str = Field(..., description="Template description")
    language: Optional[str] = Field(None, description="Default language")
    entity_types: List[str] = Field(default_factory=list, description="Entity types defined in template")


class TemplateInfo(BaseModel):
    """Detailed template information."""
    metadata: TemplateMetadata
    available_prompts: List[str] = Field(..., description="List of available prompt keys")
    delimiters: Dict[str, str] = Field(..., description="Delimiter configuration")
    extraction_settings: Dict[str, Any] = Field(default_factory=dict, description="Extraction settings")
    is_active: bool = Field(..., description="Whether this template is currently active")


class TemplateListResponse(BaseModel):
    """Response for listing templates."""
    templates: List[str] = Field(..., description="List of available template names")
    active_template: Optional[str] = Field(None, description="Currently active template name")
    templates_enabled: bool = Field(..., description="Whether template system is enabled")
    template_directory: str = Field(..., description="Template directory path")


class TemplateValidationRequest(BaseModel):
    """Request to validate a custom template."""
    template_content: str = Field(..., description="YAML template content to validate")


class TemplateValidationResponse(BaseModel):
    """Response from template validation."""
    valid: bool = Field(..., description="Whether the template is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors if any")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings if any")


class TemplateStatusResponse(BaseModel):
    """Current template system status."""
    enabled: bool = Field(..., description="Whether templates are enabled")
    active_template: Optional[str] = Field(None, description="Active template name")
    custom_template_path: Optional[str] = Field(None, description="Custom template path if used")
    template_directory: str = Field(..., description="Template directory")
    fallback_to_hardcoded: bool = Field(..., description="Whether falling back to hardcoded prompts")


# Helper Functions
# ----------------

def get_template_directory(rag: LightRAG) -> str:
    """Get the template directory path."""
    if rag.extraction_template_dir:
        return rag.extraction_template_dir

    # Default to lightrag/prompts/templates
    from lightrag.prompts.loader import PromptTemplateLoader
    loader = PromptTemplateLoader()
    return loader._get_default_template_dir()


def list_available_templates(template_dir: str) -> List[str]:
    """List all available template YAML files in the directory."""
    template_path = Path(template_dir)
    if not template_path.exists():
        return []

    templates = []
    for file in template_path.glob("*.yaml"):
        template_name = file.stem  # Filename without extension
        templates.append(template_name)

    return sorted(templates)


# API Endpoints
# -------------

@router.get("/status", response_model=TemplateStatusResponse)
async def get_template_status(
    rag: LightRAG = Depends(get_lightrag_instance)
):
    """
    Get the current status of the template system.

    Returns information about whether templates are enabled, which template
    is active, and configuration details.
    """
    prompt_manager = rag._prompt_manager

    fallback_to_hardcoded = False
    if prompt_manager:
        # Check if template loader is actually loaded
        if rag.enable_extraction_templates and not prompt_manager.template_loader:
            fallback_to_hardcoded = True

    return TemplateStatusResponse(
        enabled=rag.enable_extraction_templates,
        active_template=rag.extraction_template_name if rag.enable_extraction_templates else None,
        custom_template_path=rag.custom_template_path,
        template_directory=get_template_directory(rag),
        fallback_to_hardcoded=fallback_to_hardcoded
    )


@router.get("/list", response_model=TemplateListResponse)
async def list_templates(
    rag: LightRAG = Depends(get_lightrag_instance)
):
    """
    List all available templates in the template directory.

    Returns a list of template names that can be used, along with
    information about the currently active template.
    """
    template_dir = get_template_directory(rag)
    available_templates = list_available_templates(template_dir)

    active_template = None
    if rag.enable_extraction_templates:
        if rag.custom_template_path:
            active_template = f"custom: {rag.custom_template_path}"
        else:
            active_template = rag.extraction_template_name

    return TemplateListResponse(
        templates=available_templates,
        active_template=active_template,
        templates_enabled=rag.enable_extraction_templates,
        template_directory=template_dir
    )


@router.get("/{template_name}", response_model=TemplateInfo)
async def get_template_info(
    template_name: str,
    rag: LightRAG = Depends(get_lightrag_instance)
):
    """
    Get detailed information about a specific template.

    Args:
        template_name: Name of the template to inspect

    Returns detailed information including metadata, available prompts,
    delimiters, and extraction settings.
    """
    from lightrag.prompts import PromptTemplateLoader

    template_dir = get_template_directory(rag)

    try:
        # Load the template
        loader = PromptTemplateLoader(
            template_name=template_name,
            template_dir=template_dir,
            custom_template_path=None
        )

        # Get metadata
        metadata_dict = loader.get_metadata()
        metadata = TemplateMetadata(
            name=metadata_dict.get("name", template_name),
            version=metadata_dict.get("version", "unknown"),
            description=metadata_dict.get("description", ""),
            language=metadata_dict.get("language"),
            entity_types=metadata_dict.get("entity_types", [])
        )

        # Get available prompts
        available_prompts = loader.get_all_prompt_keys()

        # Get delimiters
        delimiters = loader.get_delimiters()

        # Get extraction settings
        extraction_settings = loader.get_extraction_settings()

        # Check if this is the active template
        is_active = (
            rag.enable_extraction_templates and
            rag.extraction_template_name == template_name and
            not rag.custom_template_path
        )

        return TemplateInfo(
            metadata=metadata,
            available_prompts=available_prompts,
            delimiters=delimiters,
            extraction_settings=extraction_settings,
            is_active=is_active
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found in {template_dir}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to load template '{template_name}': {str(e)}"
        )


@router.post("/validate", response_model=TemplateValidationResponse)
async def validate_template(
    request: TemplateValidationRequest
):
    """
    Validate a custom template YAML content.

    Checks the template structure and ensures all required fields are present.
    Useful for validating templates before deploying them.
    """
    import yaml
    from lightrag.prompts import validate_template

    try:
        # Parse YAML
        template_data = yaml.safe_load(request.template_content)

        # Validate structure
        is_valid, errors = validate_template(template_data)

        # For now, we don't have warnings, but this is extensible
        warnings = []

        return TemplateValidationResponse(
            valid=is_valid,
            errors=errors,
            warnings=warnings
        )

    except yaml.YAMLError as e:
        return TemplateValidationResponse(
            valid=False,
            errors=[f"Invalid YAML syntax: {str(e)}"],
            warnings=[]
        )
    except Exception as e:
        return TemplateValidationResponse(
            valid=False,
            errors=[f"Validation error: {str(e)}"],
            warnings=[]
        )


@router.post("/reload")
async def reload_template(
    rag: LightRAG = Depends(get_lightrag_instance)
):
    """
    Reload the current template from disk.

    Useful during development when you've modified a template and want
    to reload it without restarting the server.

    Note: This only works if templates are enabled.
    """
    if not rag.enable_extraction_templates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template system is not enabled. Cannot reload."
        )

    prompt_manager = rag._prompt_manager
    if not prompt_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PromptManager not initialized"
        )

    try:
        prompt_manager.reload_template()

        return {
            "success": True,
            "message": f"Template '{rag.extraction_template_name}' reloaded successfully",
            "template_name": rag.extraction_template_name,
            "custom_path": rag.custom_template_path
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload template: {str(e)}"
        )


class ActivateTemplateRequest(BaseModel):
    """Request to activate a template."""
    template_name: str = Field(..., description="Name of template to activate")


@router.post("/activate")
async def activate_template(
    request: ActivateTemplateRequest,
    rag: LightRAG = Depends(get_lightrag_instance)
):
    """
    Activate a different template at runtime.

    Switches the extraction template to the specified template name.
    The template must exist in the templates directory.

    Args:
        template_name: Name of the template to activate (e.g., 'default', 'arabic')

    Returns:
        Success status and active template information
    """
    if not rag.enable_extraction_templates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template system is not enabled. Set enable_extraction_templates=True to use this feature."
        )

    template_dir = get_template_directory(rag)
    available_templates = list_available_templates(template_dir)

    # Verify template exists
    if request.template_name not in available_templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{request.template_name}' not found. Available templates: {', '.join(available_templates)}"
        )

    try:
        # Switch to the new template
        rag.switch_extraction_template(template_name=request.template_name)

        return {
            "success": True,
            "message": f"Successfully activated template '{request.template_name}'",
            "active_template": request.template_name,
            "template_directory": template_dir
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate template '{request.template_name}': {str(e)}"
        )


@router.post("/upload")
async def upload_template(
    template_name: str = Field(..., description="Name for the new template (without .yaml extension)"),
    template_content: str = Field(..., description="YAML content of the template"),
    activate: bool = Field(False, description="Activate the template immediately after upload"),
    rag: LightRAG = Depends(get_lightrag_instance)
):
    """
    Upload a new template to the templates directory.

    Creates a new template YAML file in the templates directory. Optionally
    activates it immediately.

    Args:
        template_name: Name for the template file (without .yaml extension)
        template_content: Full YAML content of the template
        activate: Whether to activate this template immediately

    Returns:
        Success status and template information
    """
    import yaml

    # Validate template name
    if not template_name or '/' in template_name or '\\' in template_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template name. Must not contain path separators."
        )

    # Validate YAML syntax
    try:
        template_data = yaml.safe_load(template_content)
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML syntax: {str(e)}"
        )

    # Validate template structure
    from lightrag.prompts import validate_template
    is_valid, errors = validate_template(template_data)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template validation failed: {'; '.join(errors)}"
        )

    # Get template directory
    template_dir = get_template_directory(rag)
    template_path = Path(template_dir)

    # Create directory if it doesn't exist
    template_path.mkdir(parents=True, exist_ok=True)

    # Write template file
    template_file = template_path / f"{template_name}.yaml"

    try:
        template_file.write_text(template_content, encoding='utf-8')

        response = {
            "success": True,
            "message": f"Template '{template_name}' uploaded successfully",
            "template_name": template_name,
            "template_path": str(template_file),
            "activated": False
        }

        # Optionally activate the template
        if activate:
            if not rag.enable_extraction_templates:
                response["activation_warning"] = "Template uploaded but not activated (template system disabled)"
            else:
                try:
                    rag.switch_extraction_template(template_name=template_name)
                    response["activated"] = True
                    response["message"] = f"Template '{template_name}' uploaded and activated successfully"
                except Exception as e:
                    response["activation_error"] = f"Failed to activate: {str(e)}"

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write template file: {str(e)}"
        )
