# Entity Query System Usage Guide

This guide demonstrates how to use LightRAG's comprehensive entity query system to retrieve and filter entities, relationships, and source documents.

## Table of Contents

1. [Overview](#overview)
2. [REST API Endpoints](#rest-api-endpoints)
3. [Usage Examples](#usage-examples)
4. [Filtering and Pagination](#filtering-and-pagination)
5. [Python Service Layer](#python-service-layer)

---

## Overview

The Entity Query System provides a powerful API for querying entities and their relationships in your knowledge graph. Key features include:

- **List and search entities** with filtering by type and name patterns
- **Retrieve entity details** including descriptions and source information
- **Query relationships** with comprehensive filtering (direction, type, weight, keywords, dates, file paths)
- **Access source documents** where entities appear
- **Get statistics** about entities, relationships, and connections
- **Full entity queries** combining all information in a single request

---

## REST API Endpoints

All entity query endpoints are available under the `/entities` prefix:

### 1. List Entities
```http
GET /entities/list
```

**Query Parameters:**
- `entity_types` (optional): Comma-separated entity types (e.g., `person,organization`)
- `name_pattern` (optional): Filter by name substring (case-insensitive)
- `limit` (default: 100): Maximum entities to return
- `offset` (default: 0): Pagination offset
- `sort_by` (default: `entity_id`): Field to sort by
- `sort_order` (default: `asc`): Sort order (`asc` or `desc`)

**Example:**
```bash
curl "http://localhost:9621/entities/list?entity_types=person&limit=20&sort_by=entity_id&sort_order=asc"
```

**Response:**
```json
{
  "entities": [
    {
      "entity_id": "Alice",
      "entity_type": "person",
      "description": "A software engineer working at TechCorp...",
      "description_full_length": 150,
      "source_count": 5,
      "created_at": 1234567890
    }
  ],
  "total_count": 42,
  "returned_count": 20,
  "offset": 0,
  "limit": 20,
  "has_more": true
}
```

---

### 2. Search Entities
```http
GET /entities/search
```

**Query Parameters:**
- `q` (required): Search query string
- `entity_types` (optional): Comma-separated entity types to filter
- `limit` (default: 20): Maximum results to return

**Relevance Scoring:**
- `1.0` = Exact match
- `0.8` = Starts with query
- `0.5` = Contains query
- `0.3` = Fuzzy match

**Example:**
```bash
curl "http://localhost:9621/entities/search?q=Alice&entity_types=person&limit=10"
```

**Response:**
```json
[
  {
    "entity_id": "Alice",
    "entity_type": "person",
    "description": "A software engineer...",
    "relevance_score": 1.0,
    "source_count": 5
  },
  {
    "entity_id": "Alice Johnson",
    "entity_type": "person",
    "description": "A data scientist...",
    "relevance_score": 0.8,
    "source_count": 3
  }
]
```

---

### 3. Get Entity Types Summary
```http
GET /entities/types
```

Returns counts of entities by type.

**Example:**
```bash
curl "http://localhost:9621/entities/types"
```

**Response:**
```json
{
  "person": 150,
  "organization": 75,
  "location": 50,
  "event": 25
}
```

---

### 4. Get Entity Details
```http
GET /entities/{entity_name}
```

**Example:**
```bash
curl "http://localhost:9621/entities/Alice"
```

**Response:**
```json
{
  "entity_id": "Alice",
  "entity_type": "person",
  "description": "A software engineer working at TechCorp specializing in machine learning",
  "source_ids": ["chunk1", "chunk2", "chunk5"],
  "file_paths": ["documents/team.txt", "documents/projects.txt"],
  "timestamp": 1234567890
}
```

---

### 5. Get Entity Relationships
```http
GET /entities/{entity_name}/relationships
```

**Query Parameters:**
- `direction` (default: `both`): `incoming`, `outgoing`, or `both`
- `relation_types` (optional): Comma-separated relation types
- `related_entity_types` (optional): Filter by related entity types
- `min_weight` (default: 0.0): Minimum relationship weight
- `max_weight` (default: 1.0): Maximum relationship weight
- `keywords` (optional): Comma-separated keywords to filter by
- `file_paths` (optional): Filter by source file paths
- `date_from` (optional): Filter from this timestamp
- `date_to` (optional): Filter up to this timestamp
- `limit` (optional): Maximum relationships to return
- `offset` (default: 0): Pagination offset

**Example:**
```bash
curl "http://localhost:9621/entities/Alice/relationships?direction=outgoing&min_weight=0.7&limit=10"
```

**Response:**
```json
{
  "incoming": [],
  "outgoing": [
    {
      "source": "Alice",
      "target": "TechCorp",
      "direction": "outgoing",
      "description": "works at",
      "keywords": "employment, engineer",
      "weight": 0.9,
      "timestamp": 1234567890
    },
    {
      "source": "Alice",
      "target": "Machine Learning Project",
      "direction": "outgoing",
      "description": "leads",
      "keywords": "leadership, project",
      "weight": 0.85,
      "timestamp": 1234567900
    }
  ],
  "total_count": 2
}
```

---

### 6. Get Entity Documents
```http
GET /entities/{entity_name}/documents
```

**Query Parameters:**
- `file_paths` (optional): Comma-separated file paths to filter
- `doc_ids` (optional): Comma-separated document IDs
- `chunk_ids` (optional): Comma-separated chunk IDs
- `date_from` (optional): Filter from this timestamp
- `date_to` (optional): Filter up to this timestamp
- `max_chunks` (default: 100): Maximum chunks to return
- `offset` (default: 0): Pagination offset
- `include_full_text` (default: true): Include full chunk text
- `include_metadata` (default: true): Include chunk metadata

**Example:**
```bash
curl "http://localhost:9621/entities/Alice/documents?max_chunks=5&include_full_text=true"
```

**Response:**
```json
[
  {
    "chunk_id": "chunk1",
    "content": "Alice works as a software engineer at TechCorp.",
    "file_path": "documents/team.txt",
    "doc_id": "doc1",
    "chunk_order_index": 0,
    "tokens": 10,
    "timestamp": 1234567890
  },
  {
    "chunk_id": "chunk2",
    "content": "Alice specializes in machine learning and has 5 years of experience.",
    "file_path": "documents/team.txt",
    "doc_id": "doc1",
    "chunk_order_index": 1,
    "tokens": 12,
    "timestamp": 1234567890
  }
]
```

---

### 7. Get Full Entity Data
```http
GET /entities/{entity_name}/full
```

Get comprehensive entity data including details, relationships, documents, and statistics in a single request.

**Query Parameters:**
- `include_entity` (default: true): Include entity details
- `include_relationships` (default: true): Include relationships
- `include_documents` (default: true): Include source documents
- `include_statistics` (default: true): Include statistics
- `compute_related_entities` (default: false): Compute list of related entities
- `relationship_direction` (default: `both`): Relationship direction filter
- `max_relationships` (optional): Max relationships to return
- `min_weight` (default: 0.0): Minimum relationship weight
- `max_chunks` (default: 100): Maximum document chunks

**Example:**
```bash
curl "http://localhost:9621/entities/Alice/full?include_relationships=true&include_documents=true&max_relationships=10&max_chunks=5"
```

**Response:**
```json
{
  "entity_name": "Alice",
  "entity": {
    "entity_id": "Alice",
    "entity_type": "person",
    "description": "A software engineer working at TechCorp...",
    "source_ids": ["chunk1", "chunk2", "chunk5"],
    "file_paths": ["documents/team.txt"],
    "timestamp": 1234567890
  },
  "relationships": {
    "incoming": [...],
    "outgoing": [...],
    "total_count": 5
  },
  "documents": [...],
  "statistics": {
    "total_source_chunks": 5,
    "unique_files": 2,
    "total_relationships": 5,
    "incoming_relationships": 2,
    "outgoing_relationships": 3,
    "avg_relationship_weight": 0.85,
    "returned_chunks": 5,
    "unique_documents": 2
  },
  "related_entities": ["TechCorp", "Machine Learning Project", "Bob", "Python", "AI Team"]
}
```

---

## Usage Examples

### Example 1: Find all people working at an organization

```bash
# Step 1: Get the organization entity
curl "http://localhost:9621/entities/TechCorp"

# Step 2: Get incoming relationships (people working at TechCorp)
curl "http://localhost:9621/entities/TechCorp/relationships?direction=incoming&keywords=works"
```

### Example 2: Find documents mentioning a specific person

```bash
# Get all document chunks where Alice is mentioned
curl "http://localhost:9621/entities/Alice/documents?include_full_text=true&max_chunks=20"
```

### Example 3: Search for entities by name

```bash
# Fuzzy search for entities containing "tech"
curl "http://localhost:9621/entities/search?q=tech&limit=10"
```

### Example 4: Get entity statistics

```bash
# Get comprehensive entity data with statistics
curl "http://localhost:9621/entities/Alice/full?include_statistics=true&compute_related_entities=true"
```

### Example 5: Filter relationships by weight and type

```bash
# Get strong relationships (weight > 0.8) for Alice
curl "http://localhost:9621/entities/Alice/relationships?min_weight=0.8&direction=both"
```

---

## Filtering and Pagination

### Pagination Best Practices

Use `limit` and `offset` for efficient pagination:

```bash
# Get first page (20 entities)
curl "http://localhost:9621/entities/list?limit=20&offset=0"

# Get second page
curl "http://localhost:9621/entities/list?limit=20&offset=20"

# Get third page
curl "http://localhost:9621/entities/list?limit=20&offset=40"
```

Check the `has_more` field to determine if there are more results.

### Combining Filters

Filters can be combined for precise queries:

```bash
# Find all "person" entities in documents from a specific directory,
# with relationships created after a specific date
curl "http://localhost:9621/entities/list?entity_types=person" \
     -G --data-urlencode "name_pattern=John"

# Then get their relationships
curl "http://localhost:9621/entities/John/relationships?date_from=1234567890&file_paths=documents/2024/"
```

---

## Python Service Layer

For Python applications, you can use the `EntityQueryService` directly:

```python
from lightrag.services import EntityQueryService
from lightrag.entity_query_filters import (
    create_relationship_filters,
    create_document_filters,
    EntityQueryOptions,
)

# Initialize service
service = EntityQueryService(
    full_entities=rag.full_entities,
    chunk_entity_relation_graph=rag.chunk_entity_relation_graph,
    text_chunks=rag.text_chunks,
)

# List entities
entities = await service.list_entities(
    entity_types=["person"],
    name_pattern="John",
    limit=20,
    offset=0,
)

# Get entity details
entity = await service.get_entity_details("Alice")

# Get relationships with filters
rel_filters = create_relationship_filters(
    direction="outgoing",
    min_weight=0.7,
    keywords=["works", "manages"],
)
relationships = await service.get_entity_relationships("Alice", rel_filters)

# Get documents
doc_filters = create_document_filters(
    max_chunks=50,
    include_full_text=True,
)
documents = await service.get_entity_documents("Alice", doc_filters)

# Get full entity data
options = EntityQueryOptions(
    include_relationships=True,
    include_documents=True,
    include_statistics=True,
    compute_related_entities=True,
)
full_data = await service.query_entity_full("Alice", options)
```

---

## Filter Reference

### RelationshipFilters

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `direction` | enum | `both` | `incoming`, `outgoing`, or `both` |
| `relation_types` | list[str] | None | Filter by relationship types |
| `related_entity_types` | list[str] | None | Filter by related entity types |
| `min_weight` | float | 0.0 | Minimum relationship weight (0.0-1.0) |
| `max_weight` | float | 1.0 | Maximum relationship weight (0.0-1.0) |
| `keywords` | list[str] | None | Keywords in description/keywords field |
| `file_paths` | list[str] | None | Source file paths |
| `date_from` | int | None | Start timestamp |
| `date_to` | int | None | End timestamp |
| `limit` | int | None | Maximum results |
| `offset` | int | 0 | Pagination offset |

### DocumentFilters

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file_paths` | list[str] | None | Filter by file paths |
| `doc_ids` | list[str] | None | Filter by document IDs |
| `chunk_ids` | list[str] | None | Filter by chunk IDs |
| `date_from` | int | None | Start timestamp |
| `date_to` | int | None | End timestamp |
| `max_chunks` | int | 100 | Maximum chunks to return |
| `offset` | int | 0 | Pagination offset |
| `include_full_text` | bool | True | Include full chunk text |
| `include_metadata` | bool | True | Include chunk metadata |

---

## Tips and Best Practices

1. **Use pagination** for large result sets to avoid memory issues
2. **Filter early** - Use entity_types and name_pattern to reduce initial result set
3. **Adjust weight thresholds** - Use min_weight to focus on strong relationships
4. **Combine filters** - Use multiple filters together for precise queries
5. **Use /full endpoint** - When you need comprehensive data, use `/entities/{name}/full` instead of multiple requests
6. **Enable statistics** - Statistics provide valuable insights about entity connections
7. **Search vs List** - Use search for user-facing queries, list for programmatic access

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Successful request
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Entity not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

Example error response:
```json
{
  "detail": "Entity 'NonexistentEntity' not found"
}
```

---

For more information, see the [LightRAG documentation](https://github.com/HKUDS/LightRAG).
