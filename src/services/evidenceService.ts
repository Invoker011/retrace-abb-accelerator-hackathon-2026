import { mockEvidence } from '../data/mockData';
import { Evidence, EvidenceCategory } from '../types';
import { apiClient } from './apiClient';

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

/**
 * Evidence Service
 * Handles multimodal evidence retrieval and provenance tracking.
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
};

