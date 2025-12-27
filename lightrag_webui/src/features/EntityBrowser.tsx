import { useState, useEffect, useCallback } from 'react'
import {
  listEntities,
  searchEntities,
  getEntityFull,
  getEntityTypesSummary,
  type EntitySummary,
  type EntityFullResponse,
  type EntitySearchResult
} from '@/api/lightrag'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import Input from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Search, ChevronLeft, ChevronRight, Database, Network } from 'lucide-react'
import { toast } from 'sonner'

const EntityBrowser = () => {
  const [entities, setEntities] = useState<EntitySummary[]>([])
  const [searchResults, setSearchResults] = useState<EntitySearchResult[]>([])
  const [selectedEntity, setSelectedEntity] = useState<EntityFullResponse | null>(null)
  const [entityTypes, setEntityTypes] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(false)
  const [loadingEntity, setLoadingEntity] = useState(false)

  // Filters and pagination
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(0)
  const [totalCount, setTotalCount] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const pageSize = 20

  // Load entity types on mount
  useEffect(() => {
    loadEntityTypes()
  }, [])

  // Load entities when filters or page changes
  useEffect(() => {
    if (!searchQuery) {
      loadEntities()
    }
  }, [selectedType, currentPage])

  const loadEntityTypes = async () => {
    try {
      const types = await getEntityTypesSummary()
      setEntityTypes(types)
    } catch (error) {
      console.error('Failed to load entity types:', error)
    }
  }

  const loadEntities = async () => {
    setLoading(true)
    try {
      const response = await listEntities({
        entity_types: selectedType || undefined,
        limit: pageSize,
        offset: currentPage * pageSize,
        sort_by: 'entity_id',
        sort_order: 'asc',
      })
      setEntities(response.entities)
      setTotalCount(response.total_count)
      setHasMore(response.has_more)
      setSearchResults([])
    } catch (error: any) {
      toast.error(`Failed to load entities: ${error.message}`)
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadEntities()
      return
    }

    setLoading(true)
    try {
      const results = await searchEntities({
        q: searchQuery,
        entity_types: selectedType || undefined,
        limit: 50,
      })
      setSearchResults(results)
      setEntities([])
      setCurrentPage(0)
    } catch (error: any) {
      toast.error(`Search failed: ${error.message}`)
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleEntityClick = async (entityName: string) => {
    setLoadingEntity(true)
    try {
      const fullEntity = await getEntityFull(entityName, {
        include_entity: true,
        include_relationships: true,
        include_documents: true,
        include_statistics: true,
        compute_related_entities: true,
        max_relationships: 50,
        max_chunks: 10,
      })
      setSelectedEntity(fullEntity)
    } catch (error: any) {
      toast.error(`Failed to load entity: ${error.message}`)
      console.error(error)
    } finally {
      setLoadingEntity(false)
    }
  }

  const handleTypeFilter = (type: string) => {
    setSelectedType(type === selectedType ? '' : type)
    setCurrentPage(0)
    setSearchQuery('')
  }

  const handleClearSearch = () => {
    setSearchQuery('')
    setSearchResults([])
    loadEntities()
  }

  const displayedEntities = searchResults.length > 0
    ? searchResults.map(r => ({
        entity_id: r.entity_id,
        entity_type: r.entity_type,
        description: r.description,
        description_full_length: r.description.length,
        source_count: r.source_count,
      }))
    : entities

  return (
    <div className="flex h-full">
      {/* Left Panel: Entity List */}
      <div className="w-1/3 border-r flex flex-col">
        <div className="p-4 border-b space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Database className="h-5 w-5" />
            Entities
          </h2>

          {/* Search */}
          <div className="flex gap-2">
            <Input
              placeholder="Search entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1"
            />
            <Button onClick={handleSearch} size="sm" variant="default">
              <Search className="h-4 w-4" />
            </Button>
            {searchQuery && (
              <Button onClick={handleClearSearch} size="sm" variant="outline">
                Clear
              </Button>
            )}
          </div>

          {/* Entity Type Filters */}
          <div className="flex flex-wrap gap-2">
            {Object.entries(entityTypes).map(([type, count]) => (
              <Badge
                key={type}
                variant={selectedType === type ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => handleTypeFilter(type)}
              >
                {type} ({count})
              </Badge>
            ))}
          </div>
        </div>

        {/* Entity List */}
        <ScrollArea className="flex-1">
          {loading ? (
            <div className="p-4 text-center text-muted-foreground">
              Loading entities...
            </div>
          ) : displayedEntities.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              No entities found
            </div>
          ) : (
            <div className="p-2 space-y-2">
              {displayedEntities.map((entity) => (
                <Card
                  key={entity.entity_id}
                  className={`cursor-pointer hover:bg-accent transition-colors ${
                    selectedEntity?.entity_name === entity.entity_id ? 'border-primary' : ''
                  }`}
                  onClick={() => handleEntityClick(entity.entity_id)}
                >
                  <CardHeader className="p-3">
                    <CardTitle className="text-sm">{entity.entity_id}</CardTitle>
                    <CardDescription className="text-xs flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">
                        {entity.entity_type}
                      </Badge>
                      <span className="text-muted-foreground">
                        {entity.source_count} sources
                      </span>
                    </CardDescription>
                  </CardHeader>
                  {entity.description && (
                    <CardContent className="p-3 pt-0">
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {entity.description}
                      </p>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Pagination */}
        {!searchQuery && (
          <div className="p-4 border-t flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              {totalCount} total entities
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                disabled={currentPage === 0}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm px-2 py-1">
                Page {currentPage + 1}
              </span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage(p => p + 1)}
                disabled={!hasMore}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Right Panel: Entity Details */}
      <div className="flex-1 flex flex-col">
        {!selectedEntity ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Database className="h-12 w-12 mx-auto mb-2 opacity-20" />
              <p>Select an entity to view details</p>
            </div>
          </div>
        ) : loadingEntity ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="mb-2 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto"></div>
              <p>Loading entity details...</p>
            </div>
          </div>
        ) : (
          <ScrollArea className="flex-1">
            <div className="p-6 space-y-6">
              {/* Entity Header */}
              <div>
                <h1 className="text-2xl font-bold mb-2">{selectedEntity.entity_name}</h1>
                {selectedEntity.entity && (
                  <div className="flex gap-2 mb-4">
                    <Badge variant="default">{selectedEntity.entity.entity_type}</Badge>
                  </div>
                )}
              </div>

              <Tabs defaultValue="overview" className="w-full">
                <TabsList>
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="relationships">
                    Relationships ({selectedEntity.relationships?.total_count || 0})
                  </TabsTrigger>
                  <TabsTrigger value="documents">
                    Documents ({selectedEntity.documents?.length || 0})
                  </TabsTrigger>
                </TabsList>

                {/* Overview Tab */}
                <TabsContent value="overview" className="space-y-4">
                  {/* Description */}
                  {selectedEntity.entity?.description && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Description</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm">{selectedEntity.entity.description}</p>
                      </CardContent>
                    </Card>
                  )}

                  {/* Statistics */}
                  {selectedEntity.statistics && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Statistics</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <dl className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <dt className="text-muted-foreground">Total Relationships</dt>
                            <dd className="font-medium">{selectedEntity.statistics.total_relationships || 0}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Source Chunks</dt>
                            <dd className="font-medium">{selectedEntity.statistics.total_source_chunks || 0}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Incoming</dt>
                            <dd className="font-medium">{selectedEntity.statistics.incoming_relationships || 0}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Outgoing</dt>
                            <dd className="font-medium">{selectedEntity.statistics.outgoing_relationships || 0}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Unique Files</dt>
                            <dd className="font-medium">{selectedEntity.statistics.unique_files || 0}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Avg Relationship Weight</dt>
                            <dd className="font-medium">
                              {selectedEntity.statistics.avg_relationship_weight?.toFixed(2) || 'N/A'}
                            </dd>
                          </div>
                        </dl>
                      </CardContent>
                    </Card>
                  )}

                  {/* Related Entities */}
                  {selectedEntity.related_entities && selectedEntity.related_entities.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Related Entities</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          {selectedEntity.related_entities.map((relatedEntity) => (
                            <Badge
                              key={relatedEntity}
                              variant="outline"
                              className="cursor-pointer hover:bg-accent"
                              onClick={() => handleEntityClick(relatedEntity)}
                            >
                              {relatedEntity}
                            </Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>

                {/* Relationships Tab */}
                <TabsContent value="relationships" className="space-y-4">
                  {selectedEntity.relationships?.outgoing && selectedEntity.relationships.outgoing.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Network className="h-4 w-4" />
                          Outgoing Relationships
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {selectedEntity.relationships.outgoing.map((rel, idx) => (
                            <div key={idx} className="p-3 border rounded-lg">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline">{rel.source}</Badge>
                                  <span className="text-sm text-muted-foreground">→</span>
                                  <Badge
                                    variant="outline"
                                    className="cursor-pointer hover:bg-accent"
                                    onClick={() => handleEntityClick(rel.target)}
                                  >
                                    {rel.target}
                                  </Badge>
                                </div>
                                <Badge variant="secondary">Weight: {rel.weight.toFixed(2)}</Badge>
                              </div>
                              {rel.description && (
                                <p className="text-sm text-muted-foreground">{rel.description}</p>
                              )}
                              {rel.keywords && (
                                <p className="text-xs text-muted-foreground mt-1">
                                  Keywords: {rel.keywords}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {selectedEntity.relationships?.incoming && selectedEntity.relationships.incoming.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Network className="h-4 w-4" />
                          Incoming Relationships
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {selectedEntity.relationships.incoming.map((rel, idx) => (
                            <div key={idx} className="p-3 border rounded-lg">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <Badge
                                    variant="outline"
                                    className="cursor-pointer hover:bg-accent"
                                    onClick={() => handleEntityClick(rel.source)}
                                  >
                                    {rel.source}
                                  </Badge>
                                  <span className="text-sm text-muted-foreground">→</span>
                                  <Badge variant="outline">{rel.target}</Badge>
                                </div>
                                <Badge variant="secondary">Weight: {rel.weight.toFixed(2)}</Badge>
                              </div>
                              {rel.description && (
                                <p className="text-sm text-muted-foreground">{rel.description}</p>
                              )}
                              {rel.keywords && (
                                <p className="text-xs text-muted-foreground mt-1">
                                  Keywords: {rel.keywords}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {(!selectedEntity.relationships?.incoming?.length && !selectedEntity.relationships?.outgoing?.length) && (
                    <div className="text-center text-muted-foreground py-8">
                      No relationships found
                    </div>
                  )}
                </TabsContent>

                {/* Documents Tab */}
                <TabsContent value="documents" className="space-y-4">
                  {selectedEntity.documents && selectedEntity.documents.length > 0 ? (
                    selectedEntity.documents.map((doc) => (
                      <Card key={doc.chunk_id}>
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-sm">{doc.chunk_id}</CardTitle>
                            {doc.file_path && (
                              <Badge variant="outline" className="text-xs">
                                {doc.file_path}
                              </Badge>
                            )}
                          </div>
                        </CardHeader>
                        {doc.content && (
                          <CardContent>
                            <pre className="text-sm whitespace-pre-wrap font-sans">
                              {doc.content}
                            </pre>
                            <div className="mt-2 flex gap-2 text-xs text-muted-foreground">
                              {doc.tokens && <span>{doc.tokens} tokens</span>}
                              {doc.chunk_order_index !== undefined && (
                                <span>Order: {doc.chunk_order_index}</span>
                              )}
                            </div>
                          </CardContent>
                        )}
                      </Card>
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground py-8">
                      No documents found
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  )
}

export default EntityBrowser
