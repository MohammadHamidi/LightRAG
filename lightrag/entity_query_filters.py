"""
Entity Query Filter Models

Defines filter models for querying entities, relationships, and documents.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class RelationshipDirection(str, Enum):
    """Direction of relationships to retrieve."""
    INCOMING = "incoming"      # Relationships where entity is the target
    OUTGOING = "outgoing"      # Relationships where entity is the source
    BOTH = "both"              # Both incoming and outgoing


class SortOrder(str, Enum):
    """Sort order for results."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class RelationshipFilters:
    """
    Filters for retrieving entity relationships.

    Allows filtering relationships by various criteria including direction,
    type, weight, keywords, and source information.
    """

    direction: RelationshipDirection = RelationshipDirection.BOTH
    """Direction of relationships to retrieve (incoming, outgoing, or both)."""

    relation_types: Optional[List[str]] = None
    """Filter by specific relationship types/keywords (e.g., ['works_at', 'manages'])."""

    related_entity_types: Optional[List[str]] = None
    """Filter by types of related entities (e.g., ['person', 'organization'])."""

    min_weight: float = 0.0
    """Minimum relationship weight (default: 0.0)."""

    max_weight: float = 1.0
    """Maximum relationship weight (default: 1.0)."""

    keywords: Optional[List[str]] = None
    """Filter by keywords in relationship description or keywords field."""

    file_paths: Optional[List[str]] = None
    """Filter by source file paths where relationship was extracted."""

    date_from: Optional[int] = None
    """Filter relationships created on or after this timestamp."""

    date_to: Optional[int] = None
    """Filter relationships created on or before this timestamp."""

    limit: Optional[int] = None
    """Maximum number of relationships to return (None = no limit)."""

    offset: int = 0
    """Number of relationships to skip (for pagination)."""

    sort_by: str = "weight"
    """Field to sort by (weight, timestamp, etc.)."""

    sort_order: SortOrder = SortOrder.DESC
    """Sort order (ascending or descending)."""

    def __post_init__(self):
        """Validate filter values."""
        if self.min_weight < 0.0 or self.min_weight > 1.0:
            raise ValueError("min_weight must be between 0.0 and 1.0")

        if self.max_weight < 0.0 or self.max_weight > 1.0:
            raise ValueError("max_weight must be between 0.0 and 1.0")

        if self.min_weight > self.max_weight:
            raise ValueError("min_weight cannot be greater than max_weight")

        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be at least 1")

        if self.offset < 0:
            raise ValueError("offset cannot be negative")


@dataclass
class DocumentFilters:
    """
    Filters for retrieving entity source documents/chunks.

    Allows filtering document chunks by file path, date range, and
    controlling the amount of text returned.
    """

    file_paths: Optional[List[str]] = None
    """Filter by specific file paths."""

    doc_ids: Optional[List[str]] = None
    """Filter by specific document IDs."""

    chunk_ids: Optional[List[str]] = None
    """Filter by specific chunk IDs (source_ids)."""

    date_from: Optional[int] = None
    """Filter chunks created on or after this timestamp."""

    date_to: Optional[int] = None
    """Filter chunks created on or before this timestamp."""

    max_chunks: int = 100
    """Maximum number of chunks to return (default: 100)."""

    offset: int = 0
    """Number of chunks to skip (for pagination)."""

    include_full_text: bool = True
    """Whether to include full chunk text content (default: True)."""

    include_metadata: bool = True
    """Whether to include chunk metadata (default: True)."""

    sort_by: str = "timestamp"
    """Field to sort by (timestamp, chunk_order_index, etc.)."""

    sort_order: SortOrder = SortOrder.DESC
    """Sort order (ascending or descending)."""

    def __post_init__(self):
        """Validate filter values."""
        if self.max_chunks < 1:
            raise ValueError("max_chunks must be at least 1")

        if self.offset < 0:
            raise ValueError("offset cannot be negative")


@dataclass
class EntityQueryOptions:
    """
    Options for controlling entity query behavior.

    Combines relationship and document filters with additional options
    for controlling what data is retrieved and how it's returned.
    """

    include_entity_details: bool = True
    """Include entity metadata (type, description, etc.)."""

    include_relationships: bool = True
    """Include entity relationships."""

    include_documents: bool = True
    """Include source documents/chunks."""

    include_statistics: bool = True
    """Include statistics (counts, averages, etc.)."""

    relationship_filters: Optional[RelationshipFilters] = None
    """Filters for relationships (None = use defaults)."""

    document_filters: Optional[DocumentFilters] = None
    """Filters for documents (None = use defaults)."""

    compute_related_entities: bool = False
    """Compute and include list of all related entities."""

    max_related_entities: int = 50
    """Maximum number of related entities to return if compute_related_entities=True."""

    def __post_init__(self):
        """Initialize default filters if not provided."""
        if self.relationship_filters is None and self.include_relationships:
            self.relationship_filters = RelationshipFilters()

        if self.document_filters is None and self.include_documents:
            self.document_filters = DocumentFilters()

        if self.max_related_entities < 1:
            raise ValueError("max_related_entities must be at least 1")


# Helper functions for filter construction
# -----------------------------------------

def create_relationship_filters(
    direction: str = "both",
    relation_types: Optional[List[str]] = None,
    related_entity_types: Optional[List[str]] = None,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
    keywords: Optional[List[str]] = None,
    file_paths: Optional[List[str]] = None,
    date_from: Optional[int] = None,
    date_to: Optional[int] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> RelationshipFilters:
    """
    Helper function to create RelationshipFilters.

    Args:
        direction: Relationship direction ("incoming", "outgoing", or "both")
        relation_types: List of relationship types to filter by
        related_entity_types: List of related entity types to filter by
        min_weight: Minimum relationship weight
        max_weight: Maximum relationship weight
        keywords: Keywords to search for in relationships
        file_paths: File paths to filter by
        date_from: Start timestamp for filtering
        date_to: End timestamp for filtering
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        RelationshipFilters instance
    """
    return RelationshipFilters(
        direction=RelationshipDirection(direction),
        relation_types=relation_types,
        related_entity_types=related_entity_types,
        min_weight=min_weight,
        max_weight=max_weight,
        keywords=keywords,
        file_paths=file_paths,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


def create_document_filters(
    file_paths: Optional[List[str]] = None,
    doc_ids: Optional[List[str]] = None,
    chunk_ids: Optional[List[str]] = None,
    date_from: Optional[int] = None,
    date_to: Optional[int] = None,
    max_chunks: int = 100,
    offset: int = 0,
    include_full_text: bool = True,
    include_metadata: bool = True,
) -> DocumentFilters:
    """
    Helper function to create DocumentFilters.

    Args:
        file_paths: List of file paths to filter by
        doc_ids: List of document IDs to filter by
        chunk_ids: List of chunk IDs to filter by
        date_from: Start timestamp for filtering
        date_to: End timestamp for filtering
        max_chunks: Maximum number of chunks to return
        offset: Number of chunks to skip
        include_full_text: Whether to include full chunk text
        include_metadata: Whether to include chunk metadata

    Returns:
        DocumentFilters instance
    """
    return DocumentFilters(
        file_paths=file_paths,
        doc_ids=doc_ids,
        chunk_ids=chunk_ids,
        date_from=date_from,
        date_to=date_to,
        max_chunks=max_chunks,
        offset=offset,
        include_full_text=include_full_text,
        include_metadata=include_metadata,
    )


def create_entity_query_options(
    include_relationships: bool = True,
    include_documents: bool = True,
    relationship_direction: str = "both",
    max_relationships: Optional[int] = None,
    max_chunks: int = 100,
    compute_related_entities: bool = False,
) -> EntityQueryOptions:
    """
    Helper function to create EntityQueryOptions with common settings.

    Args:
        include_relationships: Whether to include relationships
        include_documents: Whether to include source documents
        relationship_direction: Direction of relationships to include
        max_relationships: Maximum number of relationships (None = no limit)
        max_chunks: Maximum number of document chunks
        compute_related_entities: Whether to compute related entities list

    Returns:
        EntityQueryOptions instance
    """
    relationship_filters = RelationshipFilters(
        direction=RelationshipDirection(relationship_direction),
        limit=max_relationships,
    ) if include_relationships else None

    document_filters = DocumentFilters(
        max_chunks=max_chunks,
    ) if include_documents else None

    return EntityQueryOptions(
        include_relationships=include_relationships,
        include_documents=include_documents,
        relationship_filters=relationship_filters,
        document_filters=document_filters,
        compute_related_entities=compute_related_entities,
    )
