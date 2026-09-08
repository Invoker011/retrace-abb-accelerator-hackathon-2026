import {
  mockIncidents,
  mockAssets,
  mockAssetRelationships,
  mockTimelineEvents,
  mockFindings,
} from '../data/mockData';
import {
  Incident,
  Asset,
  AssetRelationship,
  IncidentEvent,
  Finding,
} from '../types';
import { apiClient } from './apiClient';

// Helper mappers to safely handle both camelCase and snake_case API payloads
const mapIncident = (data: any): Incident => ({
  id: data.id,
  title: data.title,
  plantArea: data.plantArea || data.plant_area,
  severity: data.severity,
  status: data.status,
  date: data.date,
  startedAt: data.startedAt || data.started_at,
  resolvedAt: data.resolvedAt || data.resolved_at,
  summary: data.summary,
  leadInvestigator: data.leadInvestigator || data.lead_investigator,
  unresolvedQuestionsCount:
    data.unresolvedQuestionsCount ?? data.unresolved_questions_count ?? 0,
});

const mapEvent = (data: any): IncidentEvent => ({
  id: data.id,
  incidentId: data.incidentId || data.incident_id,
  timestamp: data.timestamp,
  displayTime: data.displayTime || data.display_time,
  relativeSeconds: data.relativeSeconds ?? data.relative_seconds ?? 0,
  assetId: data.assetId || data.asset_id,
  assetName: data.assetName || data.asset_name,
  eventType: data.eventType || data.event_type,
  title: data.title,
  description: data.description,
  evidenceId: data.evidenceId || data.evidence_id,
  evidenceRef: data.evidenceRef || data.evidence_ref,
  severity: data.severity,
  telemetrySnapshot: data.telemetrySnapshot || data.telemetry_snapshot,
});

const mapAsset = (data: any): Asset => ({
  id: data.id,
  name: data.name,
  tag: data.tag,
  type: data.type,
  plantArea: data.plantArea || data.plant_area,
  status: data.status,
  manufacturer: data.manufacturer,
  model: data.model,
  criticality: data.criticality,
  specs: data.specs || {},
  description: data.description,
});

const mapRelationship = (data: any): AssetRelationship => ({
  id: data.id,
  sourceAssetId: data.sourceAssetId || data.source_asset_id,
  targetAssetId: data.targetAssetId || data.target_asset_id,
  relationType: data.relationType || data.relation_type,
  description: data.description,
});

const mapFinding = (data: any): Finding => ({
  id: data.id,
  incidentId: data.incidentId || data.incident_id,
  category: data.category,
  statement: data.statement,
  supportingEvidenceIds: data.supportingEvidenceIds || data.supporting_evidence_ids || [],
  relatedAssetIds: data.relatedAssetIds || data.related_asset_ids || [],
  confidenceScore: data.confidenceScore ?? data.confidence_score,
  notes: data.notes,
});

/**
 * Incident Service
 * Connects to the FastAPI backend with seamless local fallback to synthetic data.
 */
export const incidentService = {
  async getIncidents(): Promise<Incident[]> {
    try {
      const data = await apiClient.get<any[]>('/api/incidents');
      if (Array.isArray(data) && data.length > 0) {
        return data.map(mapIncident);
      }
    } catch {
      // Offline or network error -> fallback to synthetic data
    }
    return [...mockIncidents];
  },

  async getIncidentById(id: string): Promise<Incident | undefined> {
    try {
      const data = await apiClient.get<any>(`/api/incidents/${id}`);
      if (data && data.id) {
        return mapIncident(data);
      }
    } catch {
      // Fallback
    }
    const incident = mockIncidents.find((inc) => inc.id.toUpperCase() === id.toUpperCase());
    return incident ? { ...incident } : undefined;
  },

  async getIncidentTimeline(incidentId: string): Promise<IncidentEvent[]> {
    try {
      const data = await apiClient.get<any[]>(`/api/incidents/${incidentId}/events`);
      if (Array.isArray(data) && data.length > 0) {
        return data.map(mapEvent).sort((a, b) => a.relativeSeconds - b.relativeSeconds);
      }
    } catch {
      // Fallback
    }
    const events = mockTimelineEvents.filter(
      (evt) => evt.incidentId.toUpperCase() === incidentId.toUpperCase()
    );
    return [...events].sort((a, b) => a.relativeSeconds - b.relativeSeconds);
  },

  async getIncidentAssets(incidentId?: string): Promise<Asset[]> {
    const id = incidentId || 'INC-2026-001';
    try {
      const data = await apiClient.get<any[]>(`/api/incidents/${id}/assets`);
      if (Array.isArray(data) && data.length > 0) {
        return data.map(mapAsset);
      }
    } catch {
      // Fallback
    }
    return [...mockAssets];
  },

  async getAssetById(assetId: string): Promise<Asset | undefined> {
    const assets = await this.getIncidentAssets();
    const asset = assets.find((a) => a.id.toUpperCase() === assetId.toUpperCase());
    return asset ? { ...asset } : undefined;
  },

  async getAssetRelationships(incidentId?: string): Promise<AssetRelationship[]> {
    const id = incidentId || 'INC-2026-001';
    try {
      const data = await apiClient.get<any[]>(`/api/incidents/${id}/relationships`);
      if (Array.isArray(data) && data.length > 0) {
        return data.map(mapRelationship);
      }
    } catch {
      // Fallback
    }
    return [...mockAssetRelationships];
  },

  async getIncidentFindings(incidentId: string): Promise<Finding[]> {
    try {
      const data = await apiClient.get<any[]>(`/api/incidents/${incidentId}/findings`);
      if (Array.isArray(data) && data.length > 0) {
        return data.map(mapFinding);
      }
    } catch {
      // Fallback
    }
    const findings = mockFindings.filter(
      (f) => f.incidentId.toUpperCase() === incidentId.toUpperCase()
    );
    return [...findings];
  },
};

