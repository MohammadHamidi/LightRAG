"""
Entity Query API Routes

REST API endpoints for querying entities, their relationships, and source documents.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from lightrag import LightRAG
from lightrag.api.routers.graph_routes import get_lightrag_instance
from lightrag.services import EntityQueryService
from lightrag.entity_query_filters import (
    RelationshipFilters,
    DocumentFilters,
    EntityQueryOptions,
    create_relationship_filters,
    create_document_filters,
)

router = APIRouter(prefix="/entities", tags=["entities"])


# Pydantic Response Models
# -------------------------

class EntitySummary(BaseModel):
    """Summary of an entity."""
    entity_id: str = Field(..., description="Entity identifier/name")
    entity_type: str = Field(..., description="Entity type (person, organization, etc.)")
    description: str = Field(..., description="Truncated description")
    description_full_length: int = Field(..., description="Full description length in characters")
    source_count: int = Field(..., description="Number of source chunks")
    created_at: Optional[int] = Field(None, description="Creation timestamp")


class EntityListResponse(BaseModel):
    """Response for entity listing."""
    entities: List[EntitySummary]
    total_count: int = Field(..., description="Total number of entities matching filters")
    returned_count: int = Field(..., description="Number of entities returned in this response")
    offset: int = Field(..., description="Pagination offset")
    limit: int = Field(..., description="Pagination limit")
    has_more: bool = Field(..., description="Whether more entities are available")


class EntitySearchResult(BaseModel):
    """Search result for entities."""
    entity_id: str
    entity_type: str
    description: str
    relevance_score: float = Field(..., description="Relevance score (0.0-1.0)")
    source_count: int


class EntityDetail(BaseModel):
    """Detailed entity information."""
    entity_id: str
    entity_type: Optional[str] = None
    description: Optional[str] = None
    source_ids: Optional[List[str]] = None
    file_paths: Optional[List[str]] = None
    timestamp: Optional[int] = None


class Relationship(BaseModel):
    """Relationship between entities."""
    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    direction: str = Field(..., description="Direction relative to queried entity (incoming/outgoing)")
    description: Optional[str] = None
    keywords: Optional[str] = None
    weight: float = Field(default=1.0, description="Relationship weight/strength")
    timestamp: Optional[int] = None


class RelationshipsResponse(BaseModel):
    """Response containing entity relationships."""
    incoming: List[Relationship] = Field(default_factory=list, description="Incoming relationships")
    outgoing: List[Relationship] = Field(default_factory=list, description="Outgoing relationships")
    total_count: int = Field(..., description="Total number of relationships")


class DocumentChunk(BaseModel):
    """Document chunk where entity appears."""
    chunk_id: str
    content: Optional[str] = None
    file_path: Optional[str] = None
    doc_id: Optional[str] = None
    chunk_order_index: Optional[int] = None
    tokens: Optional[int] = None
    timestamp: Optional[int] = None


class EntityStatistics(BaseModel):
    """Statistics about an entity."""
    total_source_chunks: Optional[int] = None
    unique_files: Optional[int] = None
    total_relationships: Optional[int] = None
    incoming_relationships: Optional[int] = None
    outgoing_relationships: Optional[int] = None
    avg_relationship_weight: Optional[float] = None
    returned_chunks: Optional[int] = None
    unique_documents: Optional[int] = None


class EntityFullResponse(BaseModel):
    """Complete entity data response."""
    entity_name: str
    entity: Optional[Dict[str, Any]] = None
    relationships: Optional[RelationshipsResponse] = None
    documents: Optional[List[DocumentChunk]] = None
    statistics: Optional[EntityStatistics] = None
    related_entities: Optional[List[str]] = None


# Helper Functions
# ----------------

def get_entity_query_service(rag: LightRAG = Depends(get_lightrag_instance)) -> EntityQueryService:
    """Get EntityQueryService instance from LightRAG."""
    return EntityQueryService(
        full_entities=rag.full_entities,
        chunk_entity_relation_graph=rag.chunk_entity_relation_graph,
        text_chunks=rag.text_chunks,
    )


# API Endpoints
# -------------

@router.get("/list", response_model=EntityListResponse)
async def list_entities(
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types to filter by"),
    name_pattern: Optional[str] = Query(None, description="Filter entities by name pattern (substring match)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entities to return"),
    offset: int = Query(0, ge=0, description="Number of entities to skip (pagination)"),
    sort_by: str = Query("entity_id", description="Field to sort by (entity_id, entity_type, created_at)"),
    sort_order: str = Query("asc", description="Sort order (asc or desc)"),
    service: EntityQueryService = Depends(get_entity_query_service),
):
    """
    List all entities with optional filtering and pagination.

    Supports:
    - Filtering by entity type
    - Filtering by name pattern (case-insensitive substring)
    - Pagination with limit/offset
    - Sorting by various fields
    """
    # Parse entity_types
    types_list = None
    if entity_types:
        types_list = [t.strip() for t in entity_types.split(",")]

    result = await service.list_entities(
        entity_types=types_list,
        name_pattern=name_pattern,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return EntityListResponse(**result)


@router.get("/search", response_model=List[EntitySearchResult])
async def search_entities(
    q: str = Query(..., min_length=1, description="Search query"),
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types to filter by"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    service: EntityQueryService = Depends(get_entity_query_service),
):
    """
    Search entities by name with relevance scoring.

    Returns entities matching the query with relevance scores:
    - 1.0 = Exact match
    - 0.8 = Starts with query
    - 0.5 = Contains query
    - 0.3 = Fuzzy match
    """
    # Parse entity_types
    types_list = None
    if entity_types:
        types_list = [t.strip() for t in entity_types.split(",")]

    results = await service.search_entities(
        query=q,
        entity_types=types_list,
        limit=limit,
    )

    return [EntitySearchResult(**entity) for entity in results]


@router.get("/types", response_model=Dict[str, int])
async def get_entity_types_summary(
    service: EntityQueryService = Depends(get_entity_query_service),
):
    """
    Get summary of all entity types and their counts.

    Returns a dictionary mapping each entity type to the number of entities of that type.
    """
    return await service.get_entity_types_summary()


@router.get("/{entity_name}", response_model=EntityDetail)
async def get_entity_details(
    entity_name: str,
    service: EntityQueryService = Depends(get_entity_query_service),
):
    """
    Get detailed information about a specific entity.

    Returns entity metadata including type, description, source chunks, and file paths.
    """
    entity_data = await service.get_entity_details(entity_name)

    if entity_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_name}' not found"
        )

    return EntityDetail(**entity_data)


@router.get("/{entity_name}/relationships", response_model=RelationshipsResponse)
async def get_entity_relationships(
    entity_name: str,
    direction: str = Query("both", description="Relationship direction (incoming, outgoing, both)"),
    relation_types: Optional[str] = Query(None, description="Comma-separated relation types/keywords"),
    related_entity_types: Optional[str] = Query(None, description="Comma-separated related entity types"),
    min_weight: float = Query(0.0, ge=0.0, le=1.0, description="Minimum relationship weight"),
    max_weight: float = Query(1.0, ge=0.0, le=1.0, description="Maximum relationship weight"),
    keywords: Optional[str] = Query(None, description="Comma-separated keywords to filter by"),
    file_paths: Optional[str] = Query(None, description="Comma-separated file paths"),
    date_from: Optional[int] = Query(None, description="Filter relationships from this timestamp"),
    date_to: Optional[int] = Query(None, description="Filter relationships up to this timestamp"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of relationships"),
    offset: int = Query(0, ge=0, description="Number of relationships to skip"),
    service: EntityQueryService = Depends(get_entity_query_service),
):
    """
    Get all relationships for an entity with comprehensive filtering.

    Supports filtering by:
    - Direction (incoming, outgoing, or both)
    - Relationship types/keywords
    - Related entity types
    - Weight range
    - Keywords in descriptions
    - Source file paths
    - Date range
    - Pagination
    """
    # Parse comma-separated lists
    relation_types_list = [t.strip() for t in relation_types.split(",")] if relation_types else None
    related_types_list = [t.strip() for t in related_entity_types.split(",")] if related_entity_types else None
    keywords_list = [k.strip() for k in keywords.split(",")] if keywords else None
    file_paths_list = [f.strip() for f in file_paths.split(",")] if file_paths else None

    # Create filters
    filters = create_relationship_filters(
        direction=direction,
        relation_types=relation_types_list,
        related_entity_types=related_types_list,
        min_weight=min_weight,
        max_weight=max_weight,
        keywords=keywords_list,
        file_paths=file_paths_list,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    result = await service.get_entity_relationships(entity_name, filters)

    return RelationshipsResponse(**result)


@router.get("/{entity_name}/documents", response_model=List[DocumentChunk])
async def get_entity_documents(
    entity_name: str,
    file_paths: Optional[str] = Query(None, description="Comma-separated file paths to filter by"),
    doc_ids: Optional[str] = Query(None, description="Comma-separated document IDs"),
    chunk_ids: Optional[str] = Query(None, description="Comma-separated chunk IDs"),
    date_from: Optional[int] = Query(None, description="Filter chunks from this timestamp"),
    date_to: Optional[int] = Query(None, description="Filter chunks up to this timestamp"),
    max_chunks: int = Query(100, ge=1, le=1000, description="Maximum number of chunks"),
    offset: int = Query(0, ge=0, description="Number of chunks to skip"),
    include_full_text: bool = Query(True, description="Include full chunk text content"),
    include_metadata: bool = Query(True, description="Include chunk metadata"),
    service: EntityQueryService = Depends(get_entity_query_service),
):
    """
    Get all source document chunks where the entity appears.

    Returns text chunks from documents where this entity was mentioned/extracted,
    with optional filtering and pagination.
    """
    # Parse comma-separated lists
    file_paths_list = [f.strip() for f in file_paths.split(",")] if file_paths else None
    doc_ids_list = [d.strip() for d in doc_ids.split(",")] if doc_ids else None
    chunk_ids_list = [c.strip() for c in chunk_ids.split(",")] if chunk_ids else None

    # Create filters
    filters = create_document_filters(
        file_paths=file_paths_list,
        doc_ids=doc_ids_list,
        chunk_ids=chunk_ids_list,
        date_from=date_from,
        date_to=date_to,
        max_chunks=max_chunks,
        offset=offset,
        include_full_text=include_full_text,
        include_metadata=include_metadata,
    )

    documents = await service.get_entity_documents(entity_name, filters)

    return [DocumentChunk(**doc) for doc in documents]


@router.get("/{entity_name}/full", response_model=EntityFullResponse)
async def get_entity_full(
    entity_name: str,
    include_entity: bool = Query(True, description="Include entity details"),
    include_relationships: bool = Query(True, description="Include relationships"),
    include_documents: bool = Query(True, description="Include source documents"),
    include_statistics: bool = Query(True, description="Include statistics"),
    compute_related_entities: bool = Query(False, description="Compute list of related entities"),
    # Relationship filters
    relationship_direction: str = Query("both", description="Relationship direction"),
    max_relationships: Optional[int] = Query(None, description="Max relationships to return"),
    min_weight: float = Query(0.0, ge=0.0, le=1.0, description="Minimum relationship weight"),
    # Document filters
    max_chunks: int = Query(100, ge=1, le=1000, description="Maximum document chunks"),
    service: EntityQueryService = Depends(get_entity_query_service),
):
    """
    Get comprehensive entity data including details, relationships, and documents.

    This endpoint combines all entity information in a single response:
    - Entity metadata (type, description, etc.)
    - All relationships (with filtering)
    - Source document chunks (with filtering)
    - Statistics (counts, averages, etc.)
    - Related entities (optional)

    Use this for a complete view of an entity and its context.
    """
    # Create filters
    relationship_filters = None
    if include_relationships:
        relationship_filters = create_relationship_filters(
            direction=relationship_direction,
            limit=max_relationships,
            min_weight=min_weight,
        )

    document_filters = None
    if include_documents:
        document_filters = create_document_filters(
            max_chunks=max_chunks,
        )

    # Create options
    options = EntityQueryOptions(
        include_entity_details=include_entity,
        include_relationships=include_relationships,
        include_documents=include_documents,
        include_statistics=include_statistics,
        relationship_filters=relationship_filters,
        document_filters=document_filters,
        compute_related_entities=compute_related_entities,
    )

    result = await service.query_entity_full(entity_name, options)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_name}' not found"
        )

    return EntityFullResponse(**result)
