import { useState, useEffect } from 'react'
import {
  getTemplateStatus,
  listTemplates,
  getTemplateInfo,
  reloadTemplate,
  type TemplateStatusResponse,
  type TemplateListResponse,
  type TemplateInfo
} from '@/api/lightrag'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { FileText, RefreshCw, CheckCircle, XCircle, Settings, FileCode } from 'lucide-react'
import { toast } from 'sonner'

const TemplateManager = () => {
  const [status, setStatus] = useState<TemplateStatusResponse | null>(null)
  const [templates, setTemplates] = useState<TemplateListResponse | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingTemplate, setLoadingTemplate] = useState(false)
  const [reloading, setReloading] = useState(false)

  useEffect(() => {
    loadStatus()
    loadTemplates()
  }, [])

  const loadStatus = async () => {
    setLoading(true)
    try {
      const statusData = await getTemplateStatus()
      setStatus(statusData)
    } catch (error: any) {
      toast.error(`Failed to load template status: ${error.message}`)
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const loadTemplates = async () => {
    setLoading(true)
    try {
      const templatesData = await listTemplates()
      setTemplates(templatesData)
    } catch (error: any) {
      toast.error(`Failed to load templates: ${error.message}`)
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleTemplateClick = async (templateName: string) => {
    setLoadingTemplate(true)
    try {
      const templateInfo = await getTemplateInfo(templateName)
      setSelectedTemplate(templateInfo)
    } catch (error: any) {
      toast.error(`Failed to load template info: ${error.message}`)
      console.error(error)
    } finally {
      setLoadingTemplate(false)
    }
  }

  const handleReload = async () => {
    setReloading(true)
    try {
      const result = await reloadTemplate()
      toast.success(result.message)
      await loadStatus()
      await loadTemplates()
    } catch (error: any) {
      toast.error(`Failed to reload template: ${error.message}`)
      console.error(error)
    } finally {
      setReloading(false)
    }
  }

  return (
    <div className="flex h-full">
      {/* Left Panel: Template List */}
      <div className="w-1/3 border-r flex flex-col">
        <div className="p-4 border-b space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Templates
            </h2>
            {status?.enabled && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleReload}
                disabled={reloading}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${reloading ? 'animate-spin' : ''}`} />
                Reload
              </Button>
            )}
          </div>

          {/* Status Card */}
          {status && (
            <Card>
              <CardHeader className="p-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  Template System Status
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 pt-0 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Status:</span>
                  <Badge variant={status.enabled ? "default" : "secondary"}>
                    {status.enabled ? (
                      <>
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Enabled
                      </>
                    ) : (
                      <>
                        <XCircle className="h-3 w-3 mr-1" />
                        Disabled
                      </>
                    )}
                  </Badge>
                </div>
                {status.active_template && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Active:</span>
                    <Badge variant="outline">{status.active_template}</Badge>
                  </div>
                )}
                {status.fallback_to_hardcoded && (
                  <div className="text-xs text-amber-600 dark:text-amber-400">
                    ⚠️ Using hardcoded prompts (fallback)
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Template List */}
        <ScrollArea className="flex-1">
          {loading ? (
            <div className="p-4 text-center text-muted-foreground">
              Loading templates...
            </div>
          ) : templates && templates.templates.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              No templates found
            </div>
          ) : (
            <div className="p-2 space-y-2">
              {templates?.templates.map((templateName) => (
                <Card
                  key={templateName}
                  className={`cursor-pointer hover:bg-accent transition-colors ${
                    selectedTemplate?.metadata.name === templateName ? 'border-primary' : ''
                  } ${
                    templates.active_template === templateName ? 'border-l-4 border-l-primary' : ''
                  }`}
                  onClick={() => handleTemplateClick(templateName)}
                >
                  <CardHeader className="p-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <FileCode className="h-4 w-4" />
                        {templateName}
                      </CardTitle>
                      {templates.active_template === templateName && (
                        <Badge variant="default" className="text-xs">
                          Active
                        </Badge>
                      )}
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Template Directory Info */}
        {templates && (
          <div className="p-4 border-t">
            <p className="text-xs text-muted-foreground">
              Directory: {templates.template_directory}
            </p>
          </div>
        )}
      </div>

      {/* Right Panel: Template Details */}
      <div className="flex-1 flex flex-col">
        {!selectedTemplate ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <FileText className="h-12 w-12 mx-auto mb-2 opacity-20" />
              <p>Select a template to view details</p>
            </div>
          </div>
        ) : loadingTemplate ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="mb-2 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto"></div>
              <p>Loading template details...</p>
            </div>
          </div>
        ) : (
          <ScrollArea className="flex-1">
            <div className="p-6 space-y-6">
              {/* Template Header */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h1 className="text-2xl font-bold">{selectedTemplate.metadata.name}</h1>
                  {selectedTemplate.is_active && (
                    <Badge variant="default">Currently Active</Badge>
                  )}
                </div>
                <p className="text-muted-foreground">{selectedTemplate.metadata.description}</p>
                <div className="flex gap-2 mt-4">
                  <Badge variant="outline">Version {selectedTemplate.metadata.version}</Badge>
                  {selectedTemplate.metadata.language && (
                    <Badge variant="outline">{selectedTemplate.metadata.language}</Badge>
                  )}
                </div>
              </div>

              {/* Metadata Card */}
              <Card>
                <CardHeader>
                  <CardTitle>Template Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Entity Types */}
                  <div>
                    <h3 className="text-sm font-medium mb-2">Entity Types</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedTemplate.metadata.entity_types.map((type) => (
                        <Badge key={type} variant="secondary">
                          {type}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Available Prompts */}
                  <div>
                    <h3 className="text-sm font-medium mb-2">Available Prompts</h3>
                    <ul className="space-y-1">
                      {selectedTemplate.available_prompts.map((prompt) => (
                        <li key={prompt} className="text-sm text-muted-foreground flex items-center gap-2">
                          <CheckCircle className="h-3 w-3 text-green-500" />
                          {prompt}
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>

              {/* Delimiters Card */}
              <Card>
                <CardHeader>
                  <CardTitle>Delimiters</CardTitle>
                  <CardDescription>
                    Special characters used for entity extraction formatting
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <dl className="space-y-2">
                    {Object.entries(selectedTemplate.delimiters).map(([key, value]) => (
                      <div key={key} className="flex items-start gap-4">
                        <dt className="text-sm font-medium w-32">{key}:</dt>
                        <dd className="text-sm text-muted-foreground font-mono bg-muted px-2 py-1 rounded">
                          {value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </CardContent>
              </Card>

              {/* Extraction Settings Card */}
              {Object.keys(selectedTemplate.extraction_settings).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Extraction Settings</CardTitle>
                    <CardDescription>
                      Configuration for entity extraction behavior
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <dl className="space-y-2">
                      {Object.entries(selectedTemplate.extraction_settings).map(([key, value]) => (
                        <div key={key} className="flex items-start gap-4">
                          <dt className="text-sm font-medium w-64">{key}:</dt>
                          <dd className="text-sm text-muted-foreground">
                            {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </CardContent>
                </Card>
              )}

              {/* Usage Instructions */}
              <Card>
                <CardHeader>
                  <CardTitle>How to Use This Template</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>
                    <h4 className="font-medium mb-1">Via Environment Variables:</h4>
                    <pre className="bg-muted p-3 rounded-lg overflow-x-auto">
                      <code>{`export ENABLE_EXTRACTION_TEMPLATES=true
export EXTRACTION_TEMPLATE_NAME=${selectedTemplate.metadata.name}`}</code>
                    </pre>
                  </div>
                  <div>
                    <h4 className="font-medium mb-1">Via Python Code:</h4>
                    <pre className="bg-muted p-3 rounded-lg overflow-x-auto">
                      <code>{`rag = LightRAG(
  working_dir="./rag_storage",
  enable_extraction_templates=True,
  extraction_template_name="${selectedTemplate.metadata.name}"
)`}</code>
                    </pre>
                  </div>
                </CardContent>
              </Card>
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  )
}

export default TemplateManager
