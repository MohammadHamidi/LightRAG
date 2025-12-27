# Template Configuration System Usage Guide

This guide explains how to use LightRAG's configurable YAML-based entity extraction template system.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration Options](#configuration-options)
4. [Template Structure](#template-structure)
5. [Creating Custom Templates](#creating-custom-templates)
6. [Template Management API](#template-management-api)
7. [Examples](#examples)

---

## Overview

LightRAG's template system allows you to:

- **Configure entity extraction prompts** via YAML templates instead of hardcoded Python
- **Switch templates** at runtime using environment variables
- **Create custom templates** for specialized domains or languages
- **Maintain backward compatibility** by falling back to hardcoded prompts when templates are disabled
- **Validate templates** before deployment using the validation API

---

## Quick Start

### Enable Templates

Set environment variables in your `.env` file:

```bash
# Enable the template system
ENABLE_EXTRACTION_TEMPLATES=true

# Use the default template
EXTRACTION_TEMPLATE_NAME=default
```

### Disable Templates (Use Hardcoded Prompts)

```bash
# Disable templates to use original hardcoded prompts
ENABLE_EXTRACTION_TEMPLATES=false
```

### Use a Custom Template

```bash
# Enable templates
ENABLE_EXTRACTION_TEMPLATES=true

# Specify a custom template file
CUSTOM_TEMPLATE_PATH=/path/to/my_custom_template.yaml
```

---

## Configuration Options

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_EXTRACTION_TEMPLATES` | boolean | `false` | Enable/disable template system |
| `EXTRACTION_TEMPLATE_NAME` | string | `"default"` | Name of template to use (without .yaml) |
| `EXTRACTION_TEMPLATE_DIR` | string | `None` | Custom directory for templates |
| `CUSTOM_TEMPLATE_PATH` | string | `None` | Path to a specific template file |

### Python Configuration

Templates can also be configured programmatically:

```python
from lightrag import LightRAG

# Enable templates with default template
rag = LightRAG(
    working_dir="./rag_storage",
    enable_extraction_templates=True,
    extraction_template_name="default"
)

# Use a custom template file
rag = LightRAG(
    working_dir="./rag_storage",
    enable_extraction_templates=True,
    custom_template_path="/path/to/my_template.yaml"
)

# Use templates from a custom directory
rag = LightRAG(
    working_dir="./rag_storage",
    enable_extraction_templates=True,
    extraction_template_name="medical",
    extraction_template_dir="/path/to/my/templates"
)

# Disable templates (use hardcoded prompts)
rag = LightRAG(
    working_dir="./rag_storage",
    enable_extraction_templates=False
)
```

---

## Template Structure

Templates are YAML files with the following structure:

```yaml
# Template metadata
template_metadata:
  name: "template_name"
  version: "1.0.0"
  description: "Description of this template"
  language: "English"  # Optional: default language
  entity_types:  # List of entity types this template recognizes
    - "person"
    - "organization"
    - "location"
    - "event"

# Prompt definitions
prompts:
  # System prompt for entity extraction
  entity_extraction_system:
    role: "You are a Knowledge Graph Specialist..."
    instructions: |
      Your task is to extract entities and relationships...
    output_format: |
      Format each entity/relationship as:
      (entity1{tuple_delimiter}type1{tuple_delimiter}description1)
    guidelines:
      - "Be comprehensive but precise"
      - "Use the specified entity types"
    variables:
      - "entity_types"
      - "tuple_delimiter"
      - "completion_delimiter"
      - "language"

  # User prompt for entity extraction
  entity_extraction_user:
    task_description: "Extract entities from the following text"
    input_label: "Text"
    output_label: "Extracted entities"
    variables:
      - "input_text"
      - "entity_types"
      - "tuple_delimiter"
      - "completion_delimiter"
      - "language"

  # Continuation prompt for gleaning
  entity_continue_extraction:
    instruction: "Continue extracting any additional entities..."
    variables:
      - "entity_types"

  # Entity description summarization prompt
  summarize_entity_descriptions:
    role: "You are an expert summarizer..."
    task: "Merge and summarize entity descriptions"
    variables:
      - "entity_name"
      - "description_list"
      - "language"

# Delimiter configuration
delimiters:
  tuple_delimiter: "<|#|>"
  completion_delimiter: "<|COMPLETE|>"
  record_delimiter: "##"

# Entity extraction settings
extraction_settings:
  max_gleaning_iterations: 1
  entity_summary_to_max_tokens: 500

# Few-shot examples (optional)
examples:
  - input: "John works at Microsoft in Seattle."
    output: |
      (John<|#|>person<|#|>John is a person who works at Microsoft)<|COMPLETE|>
      (Microsoft<|#|>organization<|#|>Microsoft is a company)<|COMPLETE|>
      (Seattle<|#|>location<|#|>Seattle is a city where Microsoft is located)<|COMPLETE|>
      (John<|#|>works at<|#|>Microsoft<|#|>John is employed by Microsoft)<|COMPLETE|>
```

---

## Creating Custom Templates

### Step 1: Copy the Default Template

```bash
cp lightrag/prompts/templates/default.yaml my_custom_template.yaml
```

### Step 2: Modify for Your Domain

Example: Medical domain template

```yaml
template_metadata:
  name: "medical"
  version: "1.0.0"
  description: "Template for medical document entity extraction"
  language: "English"
  entity_types:
    - "disease"
    - "symptom"
    - "medication"
    - "procedure"
    - "anatomy"
    - "patient"
    - "healthcare_provider"

prompts:
  entity_extraction_system:
    role: "You are a Medical Knowledge Graph Specialist with expertise in clinical documentation and medical terminology."
    instructions: |
      Your task is to extract medical entities and their relationships from clinical text.

      Focus on:
      - Diseases and conditions
      - Symptoms and signs
      - Medications and dosages
      - Medical procedures
      - Anatomical structures
      - Patient information (anonymized)
      - Healthcare providers

      Entity Types: {entity_types}

      Output Format:
      (entity1{tuple_delimiter}type1{tuple_delimiter}detailed_description1)

      For relationships:
      (entity1{tuple_delimiter}relationship{tuple_delimiter}entity2{tuple_delimiter}relationship_description)
    variables:
      - "entity_types"
      - "tuple_delimiter"
      - "completion_delimiter"
      - "language"

  entity_extraction_user:
    task_description: "Extract medical entities and relationships from the clinical note below"
    input_label: "Clinical Note"
    output_label: "Medical Entities"
    variables:
      - "input_text"

examples:
  - input: "Patient presents with acute chest pain. Prescribed aspirin 81mg daily."
    output: |
      (chest pain<|#|>symptom<|#|>Patient is experiencing chest pain)<|COMPLETE|>
      (aspirin<|#|>medication<|#|>Aspirin is a medication prescribed at 81mg daily dose)<|COMPLETE|>
      (chest pain<|#|>treated with<|#|>aspirin<|#|>Chest pain is being treated with aspirin)<|COMPLETE|>
```

### Step 3: Validate Your Template

Use the validation API before deploying:

```bash
curl -X POST http://localhost:9621/templates/validate \
  -H "Content-Type: application/json" \
  -d @my_custom_template.yaml
```

### Step 4: Deploy Your Template

```bash
# Option 1: Use custom template path
export ENABLE_EXTRACTION_TEMPLATES=true
export CUSTOM_TEMPLATE_PATH=/path/to/my_custom_template.yaml

# Option 2: Place in templates directory
cp my_custom_template.yaml lightrag/prompts/templates/medical.yaml
export ENABLE_EXTRACTION_TEMPLATES=true
export EXTRACTION_TEMPLATE_NAME=medical
```

---

## Template Management API

### Get Template Status

```bash
curl http://localhost:9621/templates/status
```

**Response:**
```json
{
  "enabled": true,
  "active_template": "default",
  "custom_template_path": null,
  "template_directory": "/path/to/lightrag/prompts/templates",
  "fallback_to_hardcoded": false
}
```

### List Available Templates

```bash
curl http://localhost:9621/templates/list
```

**Response:**
```json
{
  "templates": ["default", "medical", "legal"],
  "active_template": "default",
  "templates_enabled": true,
  "template_directory": "/path/to/lightrag/prompts/templates"
}
```

### Get Template Information

```bash
curl http://localhost:9621/templates/default
```

**Response:**
```json
{
  "metadata": {
    "name": "default",
    "version": "1.0.0",
    "description": "Default entity extraction template",
    "language": "English",
    "entity_types": ["person", "organization", "geo", "event"]
  },
  "available_prompts": [
    "entity_extraction_system",
    "entity_extraction_user",
    "entity_continue_extraction",
    "summarize_entity_descriptions"
  ],
  "delimiters": {
    "tuple_delimiter": "<|#|>",
    "completion_delimiter": "<|COMPLETE|>",
    "record_delimiter": "##"
  },
  "extraction_settings": {
    "max_gleaning_iterations": 1,
    "entity_summary_to_max_tokens": 500
  },
  "is_active": true
}
```

### Validate a Template

```bash
curl -X POST http://localhost:9621/templates/validate \
  -H "Content-Type: application/json" \
  -d '{
    "template_content": "... YAML content here ..."
  }'
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### Reload Template

Reload the current template from disk (useful during development):

```bash
curl -X POST http://localhost:9621/templates/reload
```

**Response:**
```json
{
  "success": true,
  "message": "Template 'default' reloaded successfully",
  "template_name": "default",
  "custom_path": null
}
```

---

## Examples

### Example 1: Switch to a Different Language

Create a French template:

```yaml
template_metadata:
  name: "french"
  version: "1.0.0"
  description: "Template français pour l'extraction d'entités"
  language: "French"
  entity_types:
    - "personne"
    - "organisation"
    - "lieu"
    - "événement"

prompts:
  entity_extraction_system:
    role: "Vous êtes un spécialiste des graphes de connaissances..."
    instructions: |
      Votre tâche est d'extraire les entités et relations du texte français.

      Types d'entités : {entity_types}
    variables:
      - "entity_types"
      - "tuple_delimiter"
      - "completion_delimiter"
      - "language"

  entity_extraction_user:
    task_description: "Extraire les entités du texte suivant"
    variables:
      - "input_text"
```

Deploy:
```bash
export ENABLE_EXTRACTION_TEMPLATES=true
export EXTRACTION_TEMPLATE_NAME=french
```

### Example 2: Domain-Specific Template (Legal)

```yaml
template_metadata:
  name: "legal"
  version: "1.0.0"
  description: "Template for legal document entity extraction"
  entity_types:
    - "party"
    - "court"
    - "statute"
    - "case_citation"
    - "legal_concept"
    - "jurisdiction"
    - "date"

prompts:
  entity_extraction_system:
    role: "You are a Legal Knowledge Graph Specialist with expertise in legal documents and case law."
    instructions: |
      Extract legal entities including:
      - Parties (plaintiffs, defendants, etc.)
      - Courts and jurisdictions
      - Statutes and regulations
      - Case citations
      - Legal concepts and doctrines

      Entity Types: {entity_types}
```

### Example 3: Development Workflow

```bash
# 1. Create custom template
cp lightrag/prompts/templates/default.yaml my_dev_template.yaml

# 2. Edit template
vim my_dev_template.yaml

# 3. Validate template
curl -X POST http://localhost:9621/templates/validate \
  -H "Content-Type: application/json" \
  --data-binary @my_dev_template.yaml

# 4. Test with custom path
export ENABLE_EXTRACTION_TEMPLATES=true
export CUSTOM_TEMPLATE_PATH=$(pwd)/my_dev_template.yaml

# 5. Restart service and test extraction

# 6. Make changes and reload
# Edit my_dev_template.yaml
curl -X POST http://localhost:9621/templates/reload

# 7. Deploy to production
cp my_dev_template.yaml lightrag/prompts/templates/production.yaml
export EXTRACTION_TEMPLATE_NAME=production
```

---

## Template Best Practices

### 1. Clear Instructions

Provide detailed, unambiguous instructions:

```yaml
prompts:
  entity_extraction_system:
    instructions: |
      Extract entities following these rules:
      1. Identify all named entities
      2. Classify using the specified entity types
      3. Provide concise but informative descriptions
      4. Capture relationships between entities
```

### 2. Domain-Specific Entity Types

Define entity types relevant to your domain:

```yaml
# Generic template
entity_types: ["person", "organization", "location"]

# Medical domain
entity_types: ["disease", "symptom", "medication", "procedure"]

# Financial domain
entity_types: ["company", "financial_product", "currency", "market"]
```

### 3. Include Examples

Provide few-shot examples for better extraction:

```yaml
examples:
  - input: "Example text here"
    output: "(entity1<|#|>type<|#|>description)<|COMPLETE|>"
  - input: "Another example"
    output: "(entity2<|#|>type<|#|>description)<|COMPLETE|>"
```

### 4. Version Your Templates

Use semantic versioning:

```yaml
template_metadata:
  version: "1.0.0"  # major.minor.patch
```

### 5. Document Your Templates

Add clear descriptions:

```yaml
template_metadata:
  name: "medical_v2"
  description: "Medical entity extraction template v2 - includes drug dosages and temporal relations"
```

---

## Troubleshooting

### Templates Not Loading

Check template status:
```bash
curl http://localhost:9621/templates/status
```

If `fallback_to_hardcoded: true`, check:
1. Template file exists at the specified path
2. YAML syntax is valid
3. Template passes validation
4. File permissions are correct

### Validation Errors

Common issues:
- Missing required prompt keys
- Invalid YAML syntax
- Missing required metadata fields
- Invalid entity_types structure

### Testing Templates

Use the reload endpoint during development:
```bash
# Make changes to template
curl -X POST http://localhost:9621/templates/reload

# Test extraction immediately without restarting server
```

---

## Migration from Hardcoded Prompts

If you're upgrading from a version without template support:

1. **Default behavior**: Templates are disabled by default, so existing installations continue to work
2. **Gradual migration**: Enable templates only when ready:
   ```bash
   ENABLE_EXTRACTION_TEMPLATES=true
   ```
3. **Customization**: Start with the default template and gradually customize
4. **Testing**: Test thoroughly with your documents before deploying to production

---

For more information, see the [LightRAG documentation](https://github.com/HKUDS/LightRAG).
