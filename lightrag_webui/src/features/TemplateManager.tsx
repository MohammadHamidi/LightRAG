import { useState, useEffect } from 'react'
import {
  getTemplateStatus,
  listTemplates,
  getTemplateInfo,
  getTemplateContent,
  uploadTemplate,
  activateTemplate,
  deleteTemplate,
  reloadTemplate,
  validateTemplate,
  type TemplateStatusResponse,
  type TemplateListResponse,
  type TemplateInfo
} from '@/api/lightrag'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { ScrollArea } from '@/components/ui/ScrollArea'
import Input from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/AlertDialog'
import {
  FileText,
  RefreshCw,
  CheckCircle,
  XCircle,
  Settings,
  FileCode,
  Plus,
  Edit,
  Copy,
  Trash2,
  Save,
  PlayCircle,
  AlertTriangle
} from 'lucide-react'
import { toast } from 'sonner'

type ViewMode = 'view' | 'edit' | 'create'

const TemplateManager = () => {
  const [status, setStatus] = useState<TemplateStatusResponse | null>(null)
  const [templates, setTemplates] = useState<TemplateListResponse | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateInfo | null>(null)
  const [selectedTemplateName, setSelectedTemplateName] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [loadingTemplate, setLoadingTemplate] = useState(false)
  const [reloading, setReloading] = useState(false)

  // Editor state
  const [viewMode, setViewMode] = useState<ViewMode>('view')
  const [templateContent, setTemplateContent] = useState('')
  const [templateName, setTemplateName] = useState('')
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  // Dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [newTemplateName, setNewTemplateName] = useState('')
  const [duplicateFromTemplate, setDuplicateFromTemplate] = useState('')

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
    setSelectedTemplateName(templateName)
    setLoadingTemplate(true)
    setViewMode('view')
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

  const handleEdit = async () => {
    if (!selectedTemplateName) return

    setLoadingTemplate(true)
    try {
      const content = await getTemplateContent(selectedTemplateName)
      setTemplateContent(content.content)
      setTemplateName(selectedTemplateName)
      setViewMode('edit')
      setValidationErrors([])
    } catch (error: any) {
      toast.error(`Failed to load template content: ${error.message}`)
      console.error(error)
    } finally {
      setLoadingTemplate(false)
    }
  }

  const handleCreate = () => {
    setShowCreateDialog(true)
    setNewTemplateName('')
    setDuplicateFromTemplate(selectedTemplateName || 'default')
  }

  const handleCreateConfirm = async () => {
    if (!newTemplateName.trim()) {
      toast.error('Please enter a template name')
      return
    }

    setShowCreateDialog(false)
    setLoadingTemplate(true)

    try {
      // Get content from the template to duplicate
      const content = await getTemplateContent(duplicateFromTemplate)
      setTemplateContent(content.content)
      setTemplateName(newTemplateName.trim())
      setViewMode('create')
      setValidationErrors([])
      toast.success(`Creating new template from "${duplicateFromTemplate}"`)
    } catch (error: any) {
      toast.error(`Failed to duplicate template: ${error.message}`)
      console.error(error)
    } finally {
      setLoadingTemplate(false)
    }
  }

  const handleValidate = async () => {
    setValidating(true)
    try {
      const result = await validateTemplate(templateContent)
      if (result.valid) {
        toast.success('Template is valid!')
        setValidationErrors([])
      } else {
        setValidationErrors(result.errors)
        toast.error(`Template validation failed: ${result.errors.length} errors found`)
      }
    } catch (error: any) {
      toast.error(`Validation error: ${error.message}`)
      console.error(error)
    } finally {
      setValidating(false)
    }
  }

  const handleSave = async (activateAfterSave: boolean = false) => {
    if (!templateName.trim()) {
      toast.error('Template name is required')
      return
    }

    // Validate first
    setValidating(true)
    try {
      const result = await validateTemplate(templateContent)
      if (!result.valid) {
        setValidationErrors(result.errors)
        toast.error(`Cannot save: Template has ${result.errors.length} validation errors`)
        setValidating(false)
        return
      }
      setValidationErrors([])
    } catch (error: any) {
      toast.error(`Validation failed: ${error.message}`)
      setValidating(false)
      return
    }
    setValidating(false)

    // Save
    setSaving(true)
    try {
      const result = await uploadTemplate(templateName, templateContent, activateAfterSave)
      toast.success(result.message)

      // Reload templates list
      await loadTemplates()
      await loadStatus()

      // Switch to view mode and select the saved template
      setSelectedTemplateName(templateName)
      const templateInfo = await getTemplateInfo(templateName)
      setSelectedTemplate(templateInfo)
      setViewMode('view')
    } catch (error: any) {
      toast.error(`Failed to save template: ${error.message}`)
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  const handleActivate = async () => {
    if (!selectedTemplateName) return

    try {
      const result = await activateTemplate(selectedTemplateName)
      toast.success(result.message)
      await loadStatus()
      await loadTemplates()

      // Refresh template info
      const templateInfo = await getTemplateInfo(selectedTemplateName)
      setSelectedTemplate(templateInfo)
    } catch (error: any) {
      toast.error(`Failed to activate template: ${error.message}`)
      console.error(error)
    }
  }

  const handleDelete = () => {
    setShowDeleteDialog(true)
  }

  const handleDeleteConfirm = async () => {
    setShowDeleteDialog(false)

    if (!selectedTemplateName) return

    try {
      const result = await deleteTemplate(selectedTemplateName)
      toast.success(result.message)

      // Reload templates
      await loadTemplates()
      await loadStatus()

      // Clear selection
      setSelectedTemplate(null)
      setSelectedTemplateName('')
      setViewMode('view')
    } catch (error: any) {
      toast.error(`Failed to delete template: ${error.message}`)
      console.error(error)
    }
  }

  const handleReload = async () => {
    setReloading(true)
    try {
      const result = await reloadTemplate()
      toast.success(result.message)
      await loadStatus()
      await loadTemplates()

      // Refresh current template if selected
      if (selectedTemplateName) {
        const templateInfo = await getTemplateInfo(selectedTemplateName)
        setSelectedTemplate(templateInfo)
      }
    } catch (error: any) {
      toast.error(`Failed to reload template: ${error.message}`)
      console.error(error)
    } finally {
      setReloading(false)
    }
  }

  const handleCancel = () => {
    setViewMode('view')
    setTemplateContent('')
    setValidationErrors([])
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
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="default"
                onClick={handleCreate}
              >
                <Plus className="h-4 w-4 mr-1" />
                New
              </Button>
              {status?.enabled && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleReload}
                  disabled={reloading}
                >
                  <RefreshCw className={`h-4 w-4 ${reloading ? 'animate-spin' : ''}`} />
                </Button>
              )}
            </div>
          </div>

          {/* Status Card */}
          {status && (
            <Card>
              <CardHeader className="p-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  System Status
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
                    selectedTemplateName === templateName ? 'border-primary' : ''
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

      {/* Right Panel: Template View/Editor */}
      <div className="flex-1 flex flex-col">
        {viewMode === 'view' && !selectedTemplate ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <FileText className="h-12 w-12 mx-auto mb-2 opacity-20" />
              <p>Select a template to view details</p>
              <p className="text-sm mt-2">or create a new one</p>
            </div>
          </div>
        ) : loadingTemplate ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="mb-2 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto"></div>
              <p>Loading template...</p>
            </div>
          </div>
        ) : viewMode === 'view' && selectedTemplate ? (
          // View Mode - Template Details
          <ScrollArea className="flex-1">
            <div className="p-6 space-y-6">
              {/* Header with Actions */}
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h1 className="text-2xl font-bold">{selectedTemplate.metadata.name}</h1>
                    {selectedTemplate.is_active && (
                      <Badge variant="default">Active</Badge>
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
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={handleEdit}>
                    <Edit className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                  <Button size="sm" variant="outline" onClick={handleCreate}>
                    <Copy className="h-4 w-4 mr-1" />
                    Duplicate
                  </Button>
                  {!selectedTemplate.is_active && (
                    <Button size="sm" variant="default" onClick={handleActivate}>
                      <PlayCircle className="h-4 w-4 mr-1" />
                      Activate
                    </Button>
                  )}
                  {selectedTemplateName !== 'default' && (
                    <Button size="sm" variant="destructive" onClick={handleDelete}>
                      <Trash2 className="h-4 w-4 mr-1" />
                      Delete
                    </Button>
                  )}
                </div>
              </div>

              {/* Template Information Cards - existing content */}
              <Card>
                <CardHeader>
                  <CardTitle>Template Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
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
            </div>
          </ScrollArea>
        ) : (
          // Edit/Create Mode - YAML Editor
          <div className="flex-1 flex flex-col">
            <div className="p-4 border-b space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">
                    {viewMode === 'create' ? 'Create New Template' : 'Edit Template'}
                  </h2>
                  <Input
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    placeholder="Template name"
                    className="mt-2"
                    disabled={viewMode === 'edit'}
                  />
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={handleCancel}>
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleValidate}
                    disabled={validating}
                  >
                    <CheckCircle className={`h-4 w-4 mr-1 ${validating ? 'animate-spin' : ''}`} />
                    Validate
                  </Button>
                  <Button size="sm" variant="default" onClick={() => handleSave(false)} disabled={saving}>
                    <Save className="h-4 w-4 mr-1" />
                    {saving ? 'Saving...' : 'Save'}
                  </Button>
                  <Button size="sm" variant="default" onClick={() => handleSave(true)} disabled={saving}>
                    <PlayCircle className="h-4 w-4 mr-1" />
                    Save & Activate
                  </Button>
                </div>
              </div>

              {validationErrors.length > 0 && (
                <Card className="border-destructive">
                  <CardHeader className="p-3">
                    <CardTitle className="text-sm flex items-center gap-2 text-destructive">
                      <AlertTriangle className="h-4 w-4" />
                      Validation Errors ({validationErrors.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-3 pt-0">
                    <ul className="space-y-1">
                      {validationErrors.map((error, index) => (
                        <li key={index} className="text-sm text-destructive">
                          • {error}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </div>

            <div className="flex-1 p-4">
              <Textarea
                value={templateContent}
                onChange={(e) => setTemplateContent(e.target.value)}
                className="h-full font-mono text-sm"
                placeholder="Enter YAML template content..."
              />
            </div>
          </div>
        )}
      </div>

      {/* Create Template Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Template</DialogTitle>
            <DialogDescription>
              Enter a name for your new template. It will be created as a copy of an existing template.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Template Name</label>
              <Input
                value={newTemplateName}
                onChange={(e) => setNewTemplateName(e.target.value)}
                placeholder="my-custom-template"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Duplicate From</label>
              <select
                value={duplicateFromTemplate}
                onChange={(e) => setDuplicateFromTemplate(e.target.value)}
                className="w-full p-2 border rounded-md"
              >
                {templates?.templates.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateConfirm}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Template?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{selectedTemplateName}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-destructive hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default TemplateManager
