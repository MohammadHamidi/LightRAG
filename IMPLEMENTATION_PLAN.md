# LightRAG Enhancement Implementation Plan

## Executive Summary

This plan outlines the implementation of two major features for LightRAG:
1. **Configurable Entity Extraction** - Move LLM prompts and system messages to YAML templates
2. **Single Entity Query API** - Fetch detailed entity information with relationships and documents

---

## Feature 1: Configurable Entity Extraction via YAML Templates

### 1.1 Objectives

- Extract all entity extraction prompts from hardcoded Python into YAML template files
- Support multiple extraction templates (e.g., default, scientific, legal, medical)
- Enable runtime template selection via environment variable
- Maintain backward compatibility with existing system

### 1.2 Architecture Design

```
lightrag/
├── prompts/                           # NEW: Prompt template directory
│   ├── templates/
│   │   ├── default.yaml              # Default extraction template
│   │   ├── scientific.yaml           # Scientific domain template
│   │   ├── legal.yaml                # Legal domain template
│   │   └── custom_template.yaml     # User-provided template
│   ├── loader.py                     # Template loading logic
│   └── validator.py                  # Template validation schema
├── prompt.py                          # MODIFY: Load from YAML if enabled
├── operate.py                         # MODIFY: Use template-based prompts
└── constants.py                       # ADD: Template configuration constants
```

### 1.3 YAML Template Schema

```yaml
# templates/default.yaml
template_metadata:
  name: "default"
  version: "1.0.0"
  description: "Default entity extraction template"
  language: "English"
  entity_types:
    - "organization"
    - "person"
    - "geo"
    - "event"

prompts:
  entity_extraction_system:
    role: "You are an expert entity extraction assistant..."
    instructions: |
      Extract entities and relationships from the given text.
      Follow these rules:
      1. Identify entities of types: {entity_types}
      2. Extract relationships between entities
      3. Use delimiter: {tuple_delimiter}
    format_example: |
      entity{tuple_delimiter}EntityName{tuple_delimiter}EntityType{tuple_delimiter}Description
    variables:
      - entity_types
      - tuple_delimiter
      - completion_delimiter
      - language

  entity_extraction_user:
    task_description: |
      Extract all entities and relationships from the following text.
      Language: {language}
    input_template: |
      Text to analyze:
      {input_text}
    variables:
      - input_text
      - entity_types
      - language

  entity_continue_extraction:
    instruction: |
      Continue extracting any additional entities or relationships you may have missed.
    variables:
      - input_text
      - language

  summarize_entity_descriptions:
    instruction: |
      Merge the following descriptions into a single comprehensive summary.
      Maximum length: {summary_length} words
    variables:
      - description_list
      - summary_length
      - language

examples:
  entity_extraction:
    - input: "John Smith works at Acme Corp in New York."
      output: |
        entity<|#|>John Smith<|#|>person<|#|>Employee at Acme Corp
        entity<|#|>Acme Corp<|#|>organization<|#|>Company in New York
        entity<|#|>New York<|#|>geo<|#|>Location of Acme Corp
        relationship<|#|>John Smith<|#|>Acme Corp<|#|>works_at<|#|>Employment relationship
        relationship<|#|>Acme Corp<|#|>New York<|#|>located_in<|#|>Geographic location
        <|COMPLETE|>

delimiters:
  tuple_delimiter: "<|#|>"
  completion_delimiter: "<|COMPLETE|>"
  record_delimiter: "##"

extraction_settings:
  max_gleaning: 1
  entity_types_override: null  # null = use template defaults
  force_summary_threshold: 8
  summary_max_tokens: 1200
```

### 1.4 Implementation Steps

#### Step 1.4.1: Create Template Infrastructure
- [ ] Create `lightrag/prompts/` directory structure
- [ ] Implement `PromptTemplateLoader` class in `loader.py`
  - Load YAML templates from file or custom path
  - Parse and validate template structure
  - Cache loaded templates in memory
- [ ] Implement `PromptTemplateValidator` in `validator.py`
  - Validate required fields exist
  - Check variable placeholders match
  - Verify delimiter configuration
- [ ] Create default.yaml with all existing prompts migrated

#### Step 1.4.2: Modify Configuration System
- [ ] Add to `constants.py`:
  ```python
  # Template configuration
  DEFAULT_ENABLE_TEMPLATE_SYSTEM = False
  DEFAULT_TEMPLATE_NAME = "default"
  DEFAULT_TEMPLATE_DIR = "./lightrag/prompts/templates"
  ```
- [ ] Add to `env.example`:
  ```bash
  # Entity Extraction Template System
  ENABLE_EXTRACTION_TEMPLATES=false
  EXTRACTION_TEMPLATE_NAME=default
  EXTRACTION_TEMPLATE_DIR=./lightrag/prompts/templates
  CUSTOM_TEMPLATE_PATH=  # Optional: path to custom YAML
  ```
- [ ] Update `LightRAG` dataclass to accept:
  - `enable_extraction_templates: bool = False`
  - `extraction_template_name: str = "default"`
  - `extraction_template_dir: str = "./lightrag/prompts/templates"`
  - `custom_template_path: Optional[str] = None`

#### Step 1.4.3: Update Prompt Loading Logic
- [ ] Modify `prompt.py`:
  - Add `load_template_prompts(template_config)` function
  - Keep existing `PROMPTS` dict as fallback
  - Add `get_prompt(prompt_name, template_enabled, template_loader)` wrapper
- [ ] Create `PromptManager` class:
  ```python
  class PromptManager:
      def __init__(self, enable_templates, template_name, template_dir, custom_path):
          self.enable_templates = enable_templates
          self.template_loader = None if not enable_templates else PromptTemplateLoader(...)
          self.fallback_prompts = PROMPTS  # Original hardcoded prompts

      def get_prompt(self, prompt_key, **variables):
          if self.enable_templates:
              return self.template_loader.render(prompt_key, **variables)
          else:
              return self.fallback_prompts[prompt_key].format(**variables)
  ```

#### Step 1.4.4: Integrate with Entity Extraction Pipeline
- [ ] Modify `operate.py`:
  - Pass `PromptManager` instance to `extract_entities()`
  - Update `_process_single_content()` to use `prompt_manager.get_prompt()`
  - Update all prompt references:
    - `entity_extraction_system_prompt` → `prompt_manager.get_prompt("entity_extraction_system", ...)`
    - `entity_extraction_user_prompt` → `prompt_manager.get_prompt("entity_extraction_user", ...)`
    - `entity_continue_extraction_user_prompt` → `prompt_manager.get_prompt("entity_continue_extraction", ...)`

#### Step 1.4.5: Add Template Management API Endpoints
- [ ] Create `lightrag/api/routers/template_routes.py`:
  ```python
  # Endpoints:
  GET  /templates/list           # List available templates
  GET  /templates/{name}         # Get template details
  POST /templates/validate       # Validate custom template
  POST /templates/reload         # Reload templates (admin)
  ```

#### Step 1.4.6: Testing & Validation
- [ ] Unit tests for `PromptTemplateLoader`
- [ ] Unit tests for `PromptTemplateValidator`
- [ ] Integration test: extract with default template
- [ ] Integration test: extract with custom template
- [ ] Backward compatibility test: disabled templates use original prompts

---

## Feature 2: Single Entity Query API with Relationships & Documents

### 2.1 Objectives

- Query a single entity by name/ID and retrieve:
  - Entity details (type, description, metadata)
  - All relationships (incoming and outgoing)
  - All source documents/chunks where entity appears
- Support filtering by:
  - Relationship type
  - Related entity types
  - Date range
  - File paths
  - Minimum relationship weight
- Add comprehensive REST API endpoints

### 2.2 Architecture Design

```
New API Endpoint Structure:
GET  /graph/entity/{entity_name}                # Get entity details
GET  /graph/entity/{entity_name}/relationships  # Get all relationships
GET  /graph/entity/{entity_name}/documents      # Get source documents
GET  /graph/entity/{entity_name}/full           # Get complete entity data
```

### 2.3 Data Retrieval Strategy

#### Layer 1: Entity Core Data
```python
# From: full_entities (KV storage)
{
  "entity_id": "entity_name",
  "entity_type": "organization",
  "description": "Merged description",
  "source_ids": ["chunk-1", "chunk-2", ...],
  "file_paths": ["doc1.pdf", "doc2.txt"],
  "timestamp": 1704067200
}
```

#### Layer 2: Relationships
```python
# From: chunk_entity_relation_graph (Graph storage)
# Query both incoming and outgoing edges
{
  "outgoing": [
    {
      "source": "EntityA",
      "target": "EntityB",
      "relation_type": "works_at",
      "description": "...",
      "keywords": "employment, job",
      "weight": 1.0,
      "source_ids": ["chunk-1"]
    }
  ],
  "incoming": [
    {
      "source": "EntityC",
      "target": "EntityA",
      "relation_type": "manages",
      "description": "...",
      "weight": 0.8
    }
  ]
}
```

#### Layer 3: Document Context
```python
# From: text_chunks (KV storage)
# Retrieve chunks by source_ids
{
  "documents": [
    {
      "chunk_id": "chunk-1",
      "content": "Full text content where entity appears...",
      "file_path": "docs/report.pdf",
      "doc_id": "doc-hash",
      "position": {"start": 1200, "end": 2400},
      "timestamp": 1704067200
    }
  ]
}
```

### 2.4 Implementation Steps

#### Step 2.4.1: Create Entity Query Service
- [ ] Create `lightrag/services/entity_query_service.py`:
  ```python
  class EntityQueryService:
      def __init__(self, rag: LightRAG):
          self.rag = rag

      async def get_entity_details(self, entity_name: str) -> dict:
          """Fetch entity from full_entities KV storage"""

      async def get_entity_relationships(
          self,
          entity_name: str,
          filters: RelationshipFilters
      ) -> dict:
          """Fetch relationships from graph storage"""

      async def get_entity_documents(
          self,
          entity_name: str,
          filters: DocumentFilters
      ) -> list:
          """Fetch source chunks from text_chunks"""

      async def get_entity_full(
          self,
          entity_name: str,
          include_relationships: bool = True,
          include_documents: bool = True,
          filters: dict = None
      ) -> dict:
          """Comprehensive entity data retrieval"""
  ```

#### Step 2.4.2: Add Filtering Support
- [ ] Create filter models in `lightrag/types.py`:
  ```python
  @dataclass
  class RelationshipFilters:
      relation_types: Optional[List[str]] = None
      related_entity_types: Optional[List[str]] = None
      min_weight: Optional[float] = 0.0
      max_weight: Optional[float] = 1.0
      keywords: Optional[List[str]] = None
      file_paths: Optional[List[str]] = None
      date_from: Optional[int] = None
      date_to: Optional[int] = None
      direction: str = "both"  # both, incoming, outgoing

  @dataclass
  class DocumentFilters:
      file_paths: Optional[List[str]] = None
      doc_ids: Optional[List[str]] = None
      date_from: Optional[int] = None
      date_to: Optional[int] = None
      max_chunks: int = 100
      include_full_text: bool = True
  ```

#### Step 2.4.3: Extend Storage Interfaces
- [ ] Add to `base.py` - `BaseGraphStorage`:
  ```python
  async def get_node_with_edges(
      self,
      node_id: str,
      direction: str = "both"
  ) -> Tuple[dict, List[dict], List[dict]]:
      """Returns (node_data, incoming_edges, outgoing_edges)"""

  async def filter_edges_by_attributes(
      self,
      node_id: str,
      filters: dict
  ) -> List[dict]:
      """Filter edges by weight, keywords, etc."""
  ```

- [ ] Implement in concrete storage classes:
  - `networkx_impl.py` (default)
  - `neo4j_impl.py`
  - `postgres_impl.py`

#### Step 2.4.4: Create REST API Endpoints
- [ ] Update `lightrag/api/routers/graph_routes.py`:
  ```python
  @router.get("/entity/{entity_name}")
  async def get_entity_details(
      entity_name: str,
      rag: LightRAG = Depends(get_lightrag_instance)
  ):
      """Get basic entity information"""

  @router.get("/entity/{entity_name}/relationships")
  async def get_entity_relationships(
      entity_name: str,
      direction: str = "both",
      relation_types: Optional[str] = None,  # Comma-separated
      related_entity_types: Optional[str] = None,
      min_weight: float = 0.0,
      keywords: Optional[str] = None,
      file_paths: Optional[str] = None,
      date_from: Optional[int] = None,
      date_to: Optional[int] = None,
      rag: LightRAG = Depends(get_lightrag_instance)
  ):
      """Get all relationships for an entity with filtering"""

  @router.get("/entity/{entity_name}/documents")
  async def get_entity_documents(
      entity_name: str,
      file_paths: Optional[str] = None,
      max_chunks: int = 100,
      include_full_text: bool = True,
      date_from: Optional[int] = None,
      date_to: Optional[int] = None,
      rag: LightRAG = Depends(get_lightrag_instance)
  ):
      """Get all source documents/chunks where entity appears"""

  @router.get("/entity/{entity_name}/full")
  async def get_entity_full_context(
      entity_name: str,
      include_relationships: bool = True,
      include_documents: bool = True,
      # All relationship filters
      relationship_direction: str = "both",
      relation_types: Optional[str] = None,
      min_weight: float = 0.0,
      # All document filters
      max_chunks: int = 100,
      include_full_text: bool = True,
      rag: LightRAG = Depends(get_lightrag_instance)
  ):
      """Get comprehensive entity data (details + relationships + documents)"""
  ```

#### Step 2.4.5: Response Models
- [ ] Create Pydantic response models in `lightrag/api/routers/graph_routes.py`:
  ```python
  class EntityDetailResponse(BaseModel):
      entity_id: str
      entity_type: str
      description: str
      source_count: int
      file_paths: List[str]
      created_at: int
      updated_at: Optional[int]

  class RelationshipResponse(BaseModel):
      source: str
      target: str
      relation_type: Optional[str]
      description: str
      keywords: str
      weight: float
      source_ids: List[str]
      file_paths: List[str]

  class DocumentChunkResponse(BaseModel):
      chunk_id: str
      content: str
      file_path: str
      doc_id: str
      timestamp: int

  class EntityFullResponse(BaseModel):
      entity: EntityDetailResponse
      relationships: Optional[Dict[str, List[RelationshipResponse]]]
      documents: Optional[List[DocumentChunkResponse]]
      statistics: dict  # counts, averages, etc.
  ```

#### Step 2.4.6: Add Helper Methods to LightRAG Class
- [ ] Extend `lightrag.py` with entity query methods:
  ```python
  async def query_entity(
      self,
      entity_name: str,
      include_relationships: bool = True,
      include_documents: bool = True,
      relationship_filters: Optional[RelationshipFilters] = None,
      document_filters: Optional[DocumentFilters] = None
  ) -> dict:
      """Main entry point for entity queries"""
  ```

#### Step 2.4.7: Testing
- [ ] Unit tests for `EntityQueryService`
- [ ] Integration tests for API endpoints
- [ ] Test filtering logic with various parameters
- [ ] Performance test with large entity graphs
- [ ] Test backward compatibility with existing endpoints

---

## Implementation Phases

### Phase 1: Template System Foundation (Days 1-2)
1. Create directory structure and template files
2. Implement `PromptTemplateLoader` and `PromptTemplateValidator`
3. Create default.yaml with migrated prompts
4. Add configuration constants and environment variables

### Phase 2: Template System Integration (Days 3-4)
5. Create `PromptManager` class
6. Update `operate.py` to use `PromptManager`
7. Add template management API endpoints
8. Write unit tests

### Phase 3: Entity Query Service (Days 5-6)
9. Create `EntityQueryService` class
10. Implement filter models
11. Extend storage base classes with new methods
12. Implement storage methods in NetworkX, Neo4j, Postgres

### Phase 4: Entity Query API (Days 7-8)
13. Add REST API endpoints to `graph_routes.py`
14. Create response models
15. Integrate with `LightRAG` class
16. Write integration tests

### Phase 5: Testing & Documentation (Day 9)
17. End-to-end testing
18. Performance optimization
19. Update documentation
20. Create usage examples

---

## Testing Strategy

### Unit Tests
- [ ] `test_prompt_template_loader.py` - Template loading and parsing
- [ ] `test_prompt_template_validator.py` - Validation logic
- [ ] `test_prompt_manager.py` - Prompt retrieval and rendering
- [ ] `test_entity_query_service.py` - Entity querying logic
- [ ] `test_relationship_filters.py` - Filter application

### Integration Tests
- [ ] `test_template_extraction_integration.py` - Full extraction with templates
- [ ] `test_entity_api_integration.py` - API endpoint responses
- [ ] `test_backward_compatibility.py` - Ensure existing functionality works

### Performance Tests
- [ ] Template loading performance
- [ ] Entity query performance with large graphs
- [ ] Filter performance with complex criteria

---

## Backward Compatibility Guarantees

1. **Template System**:
   - Default: Templates DISABLED (`ENABLE_EXTRACTION_TEMPLATES=false`)
   - When disabled, uses existing hardcoded prompts
   - No changes to existing API contracts

2. **Entity Query**:
   - New endpoints only, no modifications to existing ones
   - Existing `/graph/*` endpoints unchanged

3. **Configuration**:
   - All new config options have safe defaults
   - Existing env vars continue to work

---

## Configuration Examples

### Example 1: Enable Default Template
```bash
# .env
ENABLE_EXTRACTION_TEMPLATES=true
EXTRACTION_TEMPLATE_NAME=default
```

### Example 2: Use Custom Template
```bash
# .env
ENABLE_EXTRACTION_TEMPLATES=true
CUSTOM_TEMPLATE_PATH=/path/to/my_custom_template.yaml
```

### Example 3: Scientific Domain Template
```yaml
# templates/scientific.yaml
template_metadata:
  name: "scientific"
  entity_types:
    - "protein"
    - "gene"
    - "disease"
    - "drug"
    - "organism"

prompts:
  entity_extraction_system:
    role: "You are a biomedical entity extraction expert..."
    # Scientific-specific instructions
```

---

## API Usage Examples

### Example 1: Get Entity Details
```bash
curl http://localhost:9621/graph/entity/John%20Smith
```

Response:
```json
{
  "entity_id": "John Smith",
  "entity_type": "person",
  "description": "Software engineer at Acme Corp...",
  "source_count": 15,
  "file_paths": ["resume.pdf", "interview.txt"],
  "created_at": 1704067200
}
```

### Example 2: Get Relationships with Filters
```bash
curl "http://localhost:9621/graph/entity/Acme%20Corp/relationships?\
direction=outgoing&\
relation_types=employs,partners_with&\
min_weight=0.5"
```

Response:
```json
{
  "entity": "Acme Corp",
  "outgoing_relationships": [
    {
      "source": "Acme Corp",
      "target": "John Smith",
      "relation_type": "employs",
      "weight": 1.0,
      "description": "Employment relationship"
    }
  ],
  "total_count": 42,
  "filtered_count": 8
}
```

### Example 3: Get Full Entity Context
```bash
curl "http://localhost:9621/graph/entity/Acme%20Corp/full?\
include_relationships=true&\
include_documents=true&\
max_chunks=50"
```

Response:
```json
{
  "entity": {
    "entity_id": "Acme Corp",
    "entity_type": "organization",
    "description": "...",
    "source_count": 25
  },
  "relationships": {
    "outgoing": [...],
    "incoming": [...]
  },
  "documents": [
    {
      "chunk_id": "chunk-123",
      "content": "Acme Corp announced...",
      "file_path": "news_article.txt"
    }
  ],
  "statistics": {
    "total_relationships": 42,
    "total_chunks": 25,
    "unique_files": 10
  }
}
```

---

## Success Criteria

### Feature 1: Configurable Templates
- ✅ Templates can be loaded from YAML files
- ✅ Multiple templates supported (default, scientific, legal, etc.)
- ✅ Runtime template selection via env var
- ✅ Backward compatible (templates can be disabled)
- ✅ Validation prevents invalid templates
- ✅ API endpoints for template management

### Feature 2: Entity Query
- ✅ Single entity retrieval with full context
- ✅ Relationship filtering by multiple criteria
- ✅ Document chunk retrieval
- ✅ REST API endpoints functional
- ✅ Response time < 500ms for typical queries
- ✅ Comprehensive error handling

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Template parsing errors | High | Comprehensive validation + fallback to defaults |
| Performance degradation | Medium | Caching + lazy loading + indexed queries |
| Breaking changes | High | Feature flags + backward compatibility tests |
| Storage backend incompatibility | Medium | Abstract interface + per-backend implementations |

---

## Future Enhancements

1. **Template System**:
   - Template hot-reloading without server restart
   - Template versioning and migration
   - Multi-language template support
   - Template testing framework

2. **Entity Query**:
   - Graph visualization API
   - Entity similarity search
   - Temporal relationship queries
   - Aggregated entity statistics

---

## Deliverables

1. ✅ Complete implementation plan (this document)
2. 🔄 Configurable template system (YAML-based)
3. 🔄 Entity query service and API
4. 🔄 Unit and integration tests
5. 🔄 Updated documentation
6. 🔄 Example templates and usage guides

---

**Plan Status**: ✅ Complete and Ready for Implementation
**Estimated Implementation Time**: 7-9 days
**Last Updated**: 2025-12-27
