"""
Entity Query Service

Provides methods for querying single entities with their relationships and documents.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
import logging

from lightrag.entity_query_filters import (
    RelationshipFilters,
    DocumentFilters,
    EntityQueryOptions,
    RelationshipDirection,
)
from lightrag.base import BaseKVStorage, BaseGraphStorage
from lightrag.constants import GRAPH_FIELD_SEP

logger = logging.getLogger(__name__)


class EntityQueryService:
    """
    Service for querying entities with their relationships and source documents.

    Provides comprehensive entity retrieval with filtering capabilities for
    relationships and documents.
    """

    def __init__(
        self,
        full_entities: BaseKVStorage,
        chunk_entity_relation_graph: BaseGraphStorage,
        text_chunks: BaseKVStorage,
    ):
        """
        Initialize the Entity Query Service.

        Args:
            full_entities: KV storage containing entity data
            chunk_entity_relation_graph: Graph storage containing relationships
            text_chunks: KV storage containing text chunks
        """
        self.full_entities = full_entities
        self.graph = chunk_entity_relation_graph
        self.text_chunks = text_chunks

    async def get_entity_details(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Get basic entity information.

        Args:
            entity_name: Name of the entity to retrieve

        Returns:
            Entity data dictionary or None if not found
        """
        entity_data = await self.graph.get_node(entity_name)

        if entity_data is None:
            logger.warning(f"Entity '{entity_name}' not found")
            return None

        return entity_data

    async def get_entity_relationships(
        self,
        entity_name: str,
        filters: Optional[RelationshipFilters] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get relationships for an entity with optional filtering.

        Args:
            entity_name: Name of the entity
            filters: Filters to apply to relationships

        Returns:
            Dictionary with 'incoming' and 'outgoing' relationship lists
        """
        if filters is None:
            filters = RelationshipFilters()

        # Check if entity exists in graph
        has_node = await self.graph.has_node(entity_name)
        if not has_node:
            logger.warning(f"Entity '{entity_name}' not found in graph")
            return {"incoming": [], "outgoing": [], "total_count": 0}

        incoming_edges = []
        outgoing_edges = []

        # Get all edges for the entity
        all_edges = await self.graph.get_node_edges(entity_name)
        if not all_edges:
            return {"incoming": [], "outgoing": [], "total_count": 0}

        # Fetch edge data for all edges
        edges_with_data = []
        for source_id, target_id in all_edges:
            edge_data = await self.graph.get_edge(source_id, target_id)
            if edge_data:
                # Determine if this is incoming or outgoing
                if target_id == entity_name:
                    # Entity is the target, so this is incoming
                    direction = "incoming"
                    neighbor_id = source_id
                else:
                    # Entity is the source, so this is outgoing
                    direction = "outgoing"
                    neighbor_id = target_id

                edges_with_data.append((neighbor_id, edge_data, direction))

        # Get incoming relationships (where entity is target)
        if filters.direction in [RelationshipDirection.INCOMING, RelationshipDirection.BOTH]:
            incoming_raw = [(nid, data) for nid, data, dir in edges_with_data if dir == "incoming"]
            incoming_edges = await self._process_edges(
                incoming_raw, entity_name, "incoming", filters
            )
        else:
            incoming_edges = []

        # Get outgoing relationships (where entity is source)
        if filters.direction in [RelationshipDirection.OUTGOING, RelationshipDirection.BOTH]:
            outgoing_raw = [(nid, data) for nid, data, dir in edges_with_data if dir == "outgoing"]
            outgoing_edges = await self._process_edges(
                outgoing_raw, entity_name, "outgoing", filters
            )
        else:
            outgoing_edges = []

        # Apply limit and offset
        if filters.limit or filters.offset:
            incoming_edges = self._apply_pagination(
                incoming_edges, filters.limit, filters.offset
            )
            outgoing_edges = self._apply_pagination(
                outgoing_edges, filters.limit, filters.offset
            )

        return {
            "incoming": incoming_edges,
            "outgoing": outgoing_edges,
            "total_count": len(incoming_edges) + len(outgoing_edges),
        }

    async def _process_edges(
        self,
        edges: List[Tuple[str, Dict[str, Any]]],
        entity_name: str,
        direction: str,
        filters: RelationshipFilters,
    ) -> List[Dict[str, Any]]:
        """
        Process and filter edge data.

        Args:
            edges: List of (neighbor_id, edge_data) tuples
            entity_name: The entity being queried
            direction: 'incoming' or 'outgoing'
            filters: Filters to apply

        Returns:
            List of processed and filtered edge dictionaries
        """
        processed_edges = []

        for neighbor_id, edge_data in edges:
            # Determine source and target based on direction
            if direction == "incoming":
                source_id = neighbor_id
                target_id = entity_name
            else:
                source_id = entity_name
                target_id = neighbor_id

            # Build edge dictionary
            edge_dict = {
                "source": source_id,
                "target": target_id,
                "direction": direction,
                **edge_data,  # Include all edge attributes
            }

            # Apply filters
            if self._edge_matches_filters(edge_dict, neighbor_id, filters):
                processed_edges.append(edge_dict)

        # Sort edges
        processed_edges = self._sort_edges(processed_edges, filters)

        return processed_edges

    def _edge_matches_filters(
        self,
        edge: Dict[str, Any],
        neighbor_id: str,
        filters: RelationshipFilters,
    ) -> bool:
        """
        Check if an edge matches the given filters.

        Args:
            edge: Edge data dictionary
            neighbor_id: ID of the neighboring entity
            filters: Filters to check against

        Returns:
            True if edge matches all filters, False otherwise
        """
        # Filter by weight
        weight = edge.get("weight", 1.0)
        if weight < filters.min_weight or weight > filters.max_weight:
            return False

        # Filter by relation types (check keywords field)
        if filters.relation_types:
            keywords = edge.get("keywords", "")
            if not any(rt.lower() in keywords.lower() for rt in filters.relation_types):
                return False

        # Filter by keywords in description or keywords field
        if filters.keywords:
            description = edge.get("description", "")
            keywords_field = edge.get("keywords", "")
            combined_text = f"{description} {keywords_field}".lower()

            if not any(kw.lower() in combined_text for kw in filters.keywords):
                return False

        # Filter by file paths
        if filters.file_paths:
            edge_file_paths = edge.get("file_paths", [])
            if isinstance(edge_file_paths, str):
                edge_file_paths = edge_file_paths.split(GRAPH_FIELD_SEP)

            if not any(fp in edge_file_paths for fp in filters.file_paths):
                return False

        # Filter by date range
        timestamp = edge.get("timestamp") or edge.get("created_at")
        if timestamp:
            if filters.date_from and timestamp < filters.date_from:
                return False
            if filters.date_to and timestamp > filters.date_to:
                return False

        # TODO: Filter by related entity types (requires looking up neighbor entity)

        return True

    def _sort_edges(
        self,
        edges: List[Dict[str, Any]],
        filters: RelationshipFilters,
    ) -> List[Dict[str, Any]]:
        """
        Sort edges based on filter criteria.

        Args:
            edges: List of edge dictionaries
            filters: Filters containing sort criteria

        Returns:
            Sorted list of edges
        """
        sort_field = filters.sort_by
        reverse = (filters.sort_order.value == "desc")

        # Handle missing sort field
        def get_sort_key(edge):
            value = edge.get(sort_field)
            if value is None:
                # Use default values for None
                if sort_field == "weight":
                    return 0.0
                elif sort_field in ["timestamp", "created_at"]:
                    return 0
                else:
                    return ""
            return value

        try:
            return sorted(edges, key=get_sort_key, reverse=reverse)
        except Exception as e:
            logger.warning(f"Failed to sort edges by '{sort_field}': {e}")
            return edges  # Return unsorted if sorting fails

    def _apply_pagination(
        self,
        items: List[Any],
        limit: Optional[int],
        offset: int,
    ) -> List[Any]:
        """
        Apply limit and offset to a list.

        Args:
            items: List to paginate
            limit: Maximum number of items (None = no limit)
            offset: Number of items to skip

        Returns:
            Paginated list
        """
        start = offset
        end = (offset + limit) if limit else None

        return items[start:end]

    async def get_entity_documents(
        self,
        entity_name: str,
        filters: Optional[DocumentFilters] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get source documents/chunks where entity appears.

        Args:
            entity_name: Name of the entity
            filters: Filters to apply to documents

        Returns:
            List of document chunk dictionaries
        """
        if filters is None:
            filters = DocumentFilters()

        # Get entity data to find source_ids
        entity_data = await self.get_entity_details(entity_name)
        if not entity_data:
            return []

        # Get source_ids (chunk IDs where entity was mentioned)
        # Note: Graph storage uses 'source_id' (singular), but check both for compatibility
        source_ids = entity_data.get("source_id", "") or entity_data.get("source_ids", "")
        if isinstance(source_ids, str):
            source_ids = source_ids.split(GRAPH_FIELD_SEP) if source_ids else []
        elif not isinstance(source_ids, list):
            source_ids = []

        if not source_ids:
            logger.info(f"No source documents found for entity '{entity_name}'")
            return []

        # Filter source_ids by chunk_ids filter if provided
        if filters.chunk_ids:
            source_ids = [sid for sid in source_ids if sid in filters.chunk_ids]

        # Retrieve chunks
        chunks = await self.text_chunks.get_by_ids(source_ids)

        # Process and filter chunks
        processed_chunks = []
        for chunk_id, chunk_data in chunks.items():
            if chunk_data is None:
                continue

            # Apply filters
            if self._chunk_matches_filters(chunk_data, filters):
                chunk_dict = self._format_chunk(
                    chunk_id, chunk_data, filters.include_full_text, filters.include_metadata
                )
                processed_chunks.append(chunk_dict)

        # Sort chunks
        processed_chunks = self._sort_chunks(processed_chunks, filters)

        # Apply pagination
        processed_chunks = self._apply_pagination(
            processed_chunks, filters.max_chunks, filters.offset
        )

        return processed_chunks

    def _chunk_matches_filters(
        self,
        chunk_data: Dict[str, Any],
        filters: DocumentFilters,
    ) -> bool:
        """
        Check if a chunk matches the given filters.

        Args:
            chunk_data: Chunk data dictionary
            filters: Filters to check against

        Returns:
            True if chunk matches all filters, False otherwise
        """
        # Filter by file paths
        if filters.file_paths:
            chunk_file_path = chunk_data.get("file_path")
            if chunk_file_path not in filters.file_paths:
                return False

        # Filter by doc IDs
        if filters.doc_ids:
            chunk_doc_id = chunk_data.get("full_doc_id") or chunk_data.get("doc_id")
            if chunk_doc_id not in filters.doc_ids:
                return False

        # Filter by date range
        timestamp = chunk_data.get("timestamp") or chunk_data.get("created_at")
        if timestamp:
            if filters.date_from and timestamp < filters.date_from:
                return False
            if filters.date_to and timestamp > filters.date_to:
                return False

        return True

    def _format_chunk(
        self,
        chunk_id: str,
        chunk_data: Dict[str, Any],
        include_full_text: bool,
        include_metadata: bool,
    ) -> Dict[str, Any]:
        """
        Format chunk data for response.

        Args:
            chunk_id: Chunk ID
            chunk_data: Raw chunk data
            include_full_text: Whether to include full text content
            include_metadata: Whether to include metadata

        Returns:
            Formatted chunk dictionary
        """
        result = {
            "chunk_id": chunk_id,
        }

        if include_full_text:
            result["content"] = chunk_data.get("content", "")

        if include_metadata:
            result.update({
                "file_path": chunk_data.get("file_path"),
                "doc_id": chunk_data.get("full_doc_id") or chunk_data.get("doc_id"),
                "chunk_order_index": chunk_data.get("chunk_order_index"),
                "tokens": chunk_data.get("tokens"),
                "timestamp": chunk_data.get("timestamp") or chunk_data.get("created_at"),
            })

        return result

    def _sort_chunks(
        self,
        chunks: List[Dict[str, Any]],
        filters: DocumentFilters,
    ) -> List[Dict[str, Any]]:
        """
        Sort chunks based on filter criteria.

        Args:
            chunks: List of chunk dictionaries
            filters: Filters containing sort criteria

        Returns:
            Sorted list of chunks
        """
        sort_field = filters.sort_by
        reverse = (filters.sort_order.value == "desc")

        def get_sort_key(chunk):
            value = chunk.get(sort_field)
            if value is None:
                if sort_field in ["timestamp", "created_at"]:
                    return 0
                elif sort_field == "chunk_order_index":
                    return 0
                else:
                    return ""
            return value

        try:
            return sorted(chunks, key=get_sort_key, reverse=reverse)
        except Exception as e:
            logger.warning(f"Failed to sort chunks by '{sort_field}': {e}")
            return chunks

    async def query_entity_full(
        self,
        entity_name: str,
        options: Optional[EntityQueryOptions] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive entity data including details, relationships, and documents.

        Args:
            entity_name: Name of the entity to query
            options: Options controlling what data to retrieve and how

        Returns:
            Dictionary containing entity data, relationships, documents, and statistics
            or None if entity not found
        """
        if options is None:
            options = EntityQueryOptions()

        # Get entity details
        entity_data = None
        if options.include_entity_details:
            entity_data = await self.get_entity_details(entity_name)
            if entity_data is None:
                return None  # Entity not found

        # Get relationships
        relationships = None
        if options.include_relationships:
            relationships = await self.get_entity_relationships(
                entity_name,
                filters=options.relationship_filters,
            )

        # Get documents
        documents = None
        if options.include_documents:
            documents = await self.get_entity_documents(
                entity_name,
                filters=options.document_filters,
            )

        # Compute statistics
        statistics = None
        if options.include_statistics:
            statistics = self._compute_statistics(
                entity_data, relationships, documents
            )

        # Compute related entities
        related_entities = None
        if options.compute_related_entities and relationships:
            related_entities = self._extract_related_entities(
                entity_name, relationships, options.max_related_entities
            )

        # Build result
        result = {
            "entity_name": entity_name,
        }

        if entity_data:
            result["entity"] = entity_data

        if relationships:
            result["relationships"] = relationships

        if documents:
            result["documents"] = documents

        if statistics:
            result["statistics"] = statistics

        if related_entities:
            result["related_entities"] = related_entities

        return result

    def _compute_statistics(
        self,
        entity_data: Optional[Dict[str, Any]],
        relationships: Optional[Dict[str, List[Dict[str, Any]]]],
        documents: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Compute statistics about the entity.

        Args:
            entity_data: Entity data dictionary
            relationships: Relationships dictionary
            documents: List of document chunks

        Returns:
            Dictionary of statistics
        """
        stats = {}

        if entity_data:
            # Check both 'source_id' (singular, used by graph storage) and 'source_ids' (plural) for compatibility
            source_ids = entity_data.get("source_id", "") or entity_data.get("source_ids", "")
            if isinstance(source_ids, str):
                source_ids = source_ids.split(GRAPH_FIELD_SEP) if source_ids else []
            elif not isinstance(source_ids, list):
                source_ids = []

            file_paths = entity_data.get("file_path", "") or entity_data.get("file_paths", "")
            if isinstance(file_paths, str):
                file_paths = file_paths.split(GRAPH_FIELD_SEP) if file_paths else []
            elif not isinstance(file_paths, list):
                file_paths = []

            stats["total_source_chunks"] = len(source_ids)
            stats["unique_files"] = len(set(file_paths))

        if relationships:
            stats["total_relationships"] = relationships.get("total_count", 0)
            stats["incoming_relationships"] = len(relationships.get("incoming", []))
            stats["outgoing_relationships"] = len(relationships.get("outgoing", []))

            # Compute average relationship weight
            all_edges = relationships.get("incoming", []) + relationships.get("outgoing", [])
            if all_edges:
                weights = [e.get("weight", 1.0) for e in all_edges]
                stats["avg_relationship_weight"] = sum(weights) / len(weights)

        if documents:
            stats["returned_chunks"] = len(documents)
            unique_doc_ids = set(d.get("doc_id") for d in documents if d.get("doc_id"))
            stats["unique_documents"] = len(unique_doc_ids)

        return stats

    def _extract_related_entities(
        self,
        entity_name: str,
        relationships: Dict[str, List[Dict[str, Any]]],
        max_entities: int,
    ) -> List[str]:
        """
        Extract list of related entity names from relationships.

        Args:
            entity_name: The entity being queried
            relationships: Relationships dictionary
            max_entities: Maximum number of related entities to return

        Returns:
            List of related entity names
        """
        related = set()

        # Extract from incoming relationships
        for edge in relationships.get("incoming", []):
            related.add(edge.get("source"))

        # Extract from outgoing relationships
        for edge in relationships.get("outgoing", []):
            related.add(edge.get("target"))

        # Remove the entity itself if it appears
        related.discard(entity_name)

        # Convert to sorted list and limit
        related_list = sorted(list(related))
        return related_list[:max_entities]

    async def list_entities(
        self,
        entity_types: Optional[List[str]] = None,
        name_pattern: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "entity_id",
        sort_order: str = "asc",
    ) -> Dict[str, Any]:
        """
        List all entities with optional filtering and pagination.

        Args:
            entity_types: Filter by entity types (e.g., ['person', 'organization'])
            name_pattern: Filter by name pattern (case-insensitive substring match)
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            sort_by: Field to sort by (entity_id, entity_type, timestamp)
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            Dictionary with entities list, total count, and pagination info
        """
        try:
            # Get all nodes from graph storage (where entities are actually stored)
            all_nodes = await self.graph.get_all_nodes()

            # Filter and process entities
            entities = []
            seen_entities = set()  # Deduplication in case storage returns duplicates

            for node in all_nodes:
                if not node or not isinstance(node, dict):
                    continue

                # Extract entity ID from node
                entity_id = node.get("id") or node.get("entity_name") or node.get("name")
                if not entity_id or entity_id in seen_entities:
                    continue

                seen_entities.add(entity_id)

                # Apply entity type filter
                if entity_types:
                    entity_type = node.get("entity_type", "").lower()
                    if entity_type not in [et.lower() for et in entity_types]:
                        continue

                # Apply name pattern filter
                if name_pattern:
                    if name_pattern.lower() not in entity_id.lower():
                        continue

                # Build entity summary
                description = node.get("description", "")
                entity_summary = {
                    "entity_id": entity_id,
                    "entity_type": node.get("entity_type"),
                    "description": description[:200] if description else "",  # Truncate description
                    "description_full_length": len(description) if description else 0,
                }

                # Add optional metadata
                if "created_at" in node:
                    entity_summary["created_at"] = node["created_at"]
                elif "timestamp" in node:
                    entity_summary["created_at"] = node["timestamp"]

                # Count source chunks
                source_ids = node.get("source_id", "") or node.get("source_ids", "")
                if isinstance(source_ids, str):
                    source_ids = source_ids.split(GRAPH_FIELD_SEP) if source_ids else []
                elif not isinstance(source_ids, list):
                    source_ids = []
                entity_summary["source_count"] = len([s for s in source_ids if s])

                entities.append(entity_summary)

            # Sort entities
            reverse = (sort_order.lower() == "desc")
            try:
                entities = sorted(
                    entities,
                    key=lambda e: e.get(sort_by, ""),
                    reverse=reverse
                )
            except Exception as e:
                logger.warning(f"Failed to sort entities by '{sort_by}': {e}")

            # Get total count before pagination
            total_count = len(entities)

            # Apply pagination
            entities = entities[offset:offset + limit]

            return {
                "entities": entities,
                "total_count": total_count,
                "returned_count": len(entities),
                "offset": offset,
                "limit": limit,
                "has_more": (offset + len(entities)) < total_count,
            }
        except Exception as e:
            logger.error(f"Failed to list entities: {e}", exc_info=True)
            # Return empty result if there's an error (storage not initialized, etc.)
            return {
                "entities": [],
                "total_count": 0,
                "returned_count": 0,
                "offset": offset,
                "limit": limit,
                "has_more": False,
            }

    async def search_entities(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search entities by name (fuzzy/substring match).

        Args:
            query: Search query string
            entity_types: Filter by entity types
            limit: Maximum number of results

        Returns:
            List of matching entities with relevance scores
        """
        # Get all entities
        result = await self.list_entities(
            entity_types=entity_types,
            name_pattern=query,
            limit=limit,
            sort_by="entity_id",
        )

        # Add relevance scoring
        query_lower = query.lower()
        entities_with_score = []

        for entity in result["entities"]:
            entity_id = entity["entity_id"]
            entity_id_lower = entity_id.lower()

            # Calculate relevance score
            score = 0.0
            if entity_id_lower == query_lower:
                score = 1.0  # Exact match
            elif entity_id_lower.startswith(query_lower):
                score = 0.8  # Starts with query
            elif query_lower in entity_id_lower:
                score = 0.5  # Contains query
            else:
                score = 0.3  # Fuzzy match

            entity["relevance_score"] = score
            entities_with_score.append(entity)

        # Sort by relevance score
        entities_with_score.sort(key=lambda e: e["relevance_score"], reverse=True)

        return entities_with_score

    async def get_entity_types_summary(self) -> Dict[str, int]:
        """
        Get summary of all entity types and their counts.

        Returns:
            Dictionary mapping entity_type to count
        """
        try:
            # Get all nodes from graph storage
            all_nodes = await self.graph.get_all_nodes()

            # Count by type with deduplication
            type_counts = {}
            seen_entities = set()

            for node in all_nodes:
                if not node or not isinstance(node, dict):
                    continue

                # Extract entity ID for deduplication
                entity_id = node.get("id") or node.get("entity_name") or node.get("name")
                if not entity_id or entity_id in seen_entities:
                    continue

                seen_entities.add(entity_id)

                entity_type = node.get("entity_type", "unknown")
                type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

            return type_counts
        except Exception as e:
            logger.error(f"Failed to get entity types summary: {e}", exc_info=True)
            # Return empty dict if there's an error (storage not initialized, etc.)
            return {}
