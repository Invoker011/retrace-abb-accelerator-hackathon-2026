import { mockEvidence } from '../data/mockData';
import { Evidence, EvidenceCategory, UploadedEvidenceItem } from '../types';
import { apiClient } from './apiClient';

let localUploadedItems: UploadedEvidenceItem[] = [];

const mapEvidence = (data: any): Evidence => ({
  id: data.id,
  filename: data.filename,
  source: data.source,
  sourceType: (data.sourceType || data.source_type) as EvidenceCategory,
  timestamp: data.timestamp || data.original_timestamp,
  normalizedTimestamp: data.normalizedTimestamp || data.normalized_timestamp,
  assetId: data.assetId || data.asset_id,
  assetName: data.assetName || data.asset_name || data.asset_id,
  extractedEvent: data.extractedEvent || data.extracted_content,
  confidence: data.confidence,
  originalEvidenceRef: data.originalEvidenceRef || data.original_reference,
  fileSize: data.fileSize || data.file_size || (data.metadata?.file_size ?? '1.0 MB'),
  format: data.format || data.metadata?.file_type || 'csv',
  previewRows: data.previewRows || data.preview_rows,
  rawContent: data.rawContent || data.raw_content,
});

const mapUploadedEvidence = (data: any): UploadedEvidenceItem => ({
  evidenceId: data.evidenceId || data.evidence_id,
  incidentId: data.incidentId || data.incident_id,
  sourceType: data.sourceType || data.source_type,
  originalFilename: data.originalFilename || data.original_filename,
  storedFilename: data.storedFilename || data.stored_filename,
  contentType: data.contentType || data.content_type,
  fileSize: Number(data.fileSize || data.file_size || 0),
  assetId: data.assetId || data.asset_id || null,
  description: data.description || null,
  storageUri: data.storageUri || data.storage_uri,
  uploadedAt: data.uploadedAt || data.uploaded_at,
  processingStatus: data.processingStatus || data.processing_status || 'UPLOADED',
  sha256Hash: data.sha256Hash || data.sha256_hash,
  metadata: data.metadata || {},
});

/**
 * Evidence Service
 * Handles multimodal evidence retrieval, provenance tracking, and secure uploads.
 * Connects to FastAPI backend with automatic fallback to mock data.
 */
export const evidenceService = {
  async getEvidenceList(incidentId: string = 'INC-2026-001'): Promise<Evidence[]> {
    try {
      const data = await apiClient.get<any[]>(`/api/incidents/${incidentId}/evidence`);
      if (Array.isArray(data) && data.length > 0) {
        return data.map(mapEvidence);
      }
    } catch {
      // Fallback
    }
    return [...mockEvidence];
  },

  async getEvidenceById(id: string): Promise<Evidence | undefined> {
    try {
      const data = await apiClient.get<any>(`/api/evidence/${id}`);
      if (data && data.id) {
        return mapEvidence(data);
      }
    } catch {
      // Fallback
    }
    const item = mockEvidence.find((e) => e.id.toUpperCase() === id.toUpperCase());
    return item ? { ...item } : undefined;
  },

  async getEvidenceByCategory(category: EvidenceCategory): Promise<Evidence[]> {
    const all = await this.getEvidenceList();
    return all.filter((e) => e.sourceType === category);
  },

  async getEvidenceForIncident(incidentId: string): Promise<Evidence[]> {
    return this.getEvidenceList(incidentId);
  },

  async searchEvidence(query: string): Promise<Evidence[]> {
    const all = await this.getEvidenceList();
    const q = query.toLowerCase().trim();
    if (!q) return all;
    return all.filter(
      (e) =>
        e.filename.toLowerCase().includes(q) ||
        e.extractedEvent.toLowerCase().includes(q) ||
        e.assetName.toLowerCase().includes(q) ||
        e.sourceType.toLowerCase().includes(q) ||
        e.originalEvidenceRef.toLowerCase().includes(q)
    );
  },

  /**
   * Upload industrial evidence file attached to an incident
   */
  async uploadEvidence(
    incidentId: string,
    file: File,
    sourceType: string,
    assetId?: string,
    description?: string
  ): Promise<UploadedEvidenceItem> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_type', sourceType);
    if (assetId) formData.append('asset_id', assetId);
    if (description) formData.append('description', description);

    try {
      const res = await apiClient.upload<any>(
        `/api/incidents/${incidentId}/evidence/upload`,
        formData
      );
      const mapped = mapUploadedEvidence(res);
      localUploadedItems.unshift(mapped);
      return mapped;
    } catch (err) {
      console.warn('[RETRACE] Upload API failed or offline, falling back to local session store:', err);
      // Fallback client simulation if offline / mock mode
      const simulated: UploadedEvidenceItem = {
        evidenceId: `EVD-UPL-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
        incidentId,
        sourceType,
        originalFilename: file.name,
        storedFilename: `local_${file.name}`,
        contentType: file.type || 'application/octet-stream',
        fileSize: file.size,
        assetId: assetId || null,
        description: description || null,
        storageUri: `file://local/incidents/${incidentId}/evidence/${file.name}`,
        uploadedAt: new Date().toISOString(),
        processingStatus: 'UPLOADED',
        sha256Hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        metadata: {
          format: file.name.split('.').pop()?.toLowerCase() || 'unknown',
          preview: 'File captured in local browser memory store (mock mode).',
        },
      };
      localUploadedItems.unshift(simulated);
      return simulated;
    }
  },

  /**
   * Get all uploaded evidence items for an incident
   */
  async getUploadedEvidence(incidentId: string = 'INC-2026-001'): Promise<UploadedEvidenceItem[]> {
    try {
      const data = await apiClient.get<any[]>(`/api/incidents/${incidentId}/evidence/uploads`);
      if (Array.isArray(data)) {
        const mappedFromApi = data.map(mapUploadedEvidence);
        // Merge with any in-memory items not yet present
        const apiIds = new Set(mappedFromApi.map((i) => i.evidenceId));
        const extraLocal = localUploadedItems.filter(
          (l) => l.incidentId === incidentId && !apiIds.has(l.evidenceId)
        );
        return [...mappedFromApi, ...extraLocal];
      }
    } catch {
      // Return local cache if API failed
    }
    return localUploadedItems.filter((l) => l.incidentId === incidentId);
  },

  /**
   * Get single uploaded evidence item by ID
   */
  async getUploadedEvidenceById(evidenceId: string): Promise<UploadedEvidenceItem | undefined> {
    try {
      const data = await apiClient.get<any>(`/api/evidence/uploads/${evidenceId}`);
      if (data && (data.evidenceId || data.evidence_id)) {
        return mapUploadedEvidence(data);
      }
    } catch {
      // Fallback to local cache
    }
    return localUploadedItems.find((i) => i.evidenceId === evidenceId);
  },

  /**
   * Delete uploaded evidence item
   */
  async deleteUploadedEvidence(evidenceId: string): Promise<boolean> {
    try {
      await apiClient.delete(`/api/evidence/uploads/${evidenceId}`);
    } catch {
      // Continue to clean up local cache regardless
    }
    localUploadedItems = localUploadedItems.filter((i) => i.evidenceId !== evidenceId);
    return true;
  },
};


