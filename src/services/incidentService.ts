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
  IncidentReplayResponse,
  ReplayRecordedValue,
  ReplayEvidenceReference,
  ReplayRelationshipContext,
  ReplayAssetState,
  ReplayEvent,
  PreventionPathsRequest,
  PreventionPathsResponse,
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

  async getIncidentReplay(
    incidentId: string,
    startOffsetSeconds?: number,
    endOffsetSeconds?: number
  ): Promise<IncidentReplayResponse | undefined> {
    const params = new URLSearchParams();
    if (startOffsetSeconds !== undefined && startOffsetSeconds !== null) {
      params.set('start_offset_seconds', String(startOffsetSeconds));
    }
    if (endOffsetSeconds !== undefined && endOffsetSeconds !== null) {
      params.set('end_offset_seconds', String(endOffsetSeconds));
    }
    const query = params.toString() ? `?${params.toString()}` : '';

    try {
      const data = await apiClient.get<IncidentReplayResponse>(
        `/api/incidents/${incidentId}/replay${query}`
      );
      if (data && (data.incident_id || (data as any).incidentId)) {
        return normalizeIncidentReplay(data);
      }
    } catch (err) {
      // Propagate error to let UI render proper error & retry state
      console.error('[RETRACE] getIncidentReplay failed:', err);
      throw err;
    }
    return undefined;
  },

  async getPreventionPaths(
    incidentId: string,
    request?: PreventionPathsRequest
  ): Promise<PreventionPathsResponse> {
    const payload = {
      query: request?.query || 'What could potentially have prevented or mitigated this incident?',
      top_k: request?.top_k ?? request?.topK ?? 10,
    };
    return await apiClient.post<PreventionPathsResponse>(
      `/api/incidents/${incidentId}/prevention-paths`,
      payload
    );
  },
};

export function normalizeIncidentReplay(data: any): IncidentReplayResponse {
  const normRecordedValue = (rv: any): ReplayRecordedValue => ({
    name: rv.name || '',
    value: rv.value,
    unit: rv.unit ?? null,
    source_evidence_id: rv.source_evidence_id ?? rv.sourceEvidenceId ?? null,
    sourceEvidenceId: rv.sourceEvidenceId ?? rv.source_evidence_id ?? null,
  });

  const normEvidenceRef = (ev: any): ReplayEvidenceReference => ({
    evidence_id: ev.evidence_id || ev.evidenceId || '',
    evidenceId: ev.evidenceId || ev.evidence_id || '',
    filename: ev.filename || '',
    source_type: ev.source_type || ev.sourceType || '',
    sourceType: ev.sourceType || ev.source_type || '',
    asset_id: ev.asset_id ?? ev.assetId ?? null,
    assetId: ev.assetId ?? ev.asset_id ?? null,
    timestamp: ev.timestamp ?? null,
    original_reference: ev.original_reference ?? ev.originalReference ?? null,
    originalReference: ev.originalReference ?? ev.original_reference ?? null,
  });

  const normRelationship = (gr: any): ReplayRelationshipContext => ({
    source: gr.source || '',
    relationship: gr.relationship || '',
    target: gr.target || '',
    description: gr.description ?? null,
  });

  const normAssetState = (st: any): ReplayAssetState | null => {
    if (!st) return null;
    const rvs = (st.recorded_values || st.recordedValues || []).map(normRecordedValue);
    return {
      asset_id: st.asset_id || st.assetId || '',
      assetId: st.assetId || st.asset_id || '',
      asset_name: st.asset_name ?? st.assetName ?? null,
      assetName: st.assetName ?? st.asset_name ?? null,
      operational_status: st.operational_status ?? st.operationalStatus ?? null,
      operationalStatus: st.operationalStatus ?? st.operational_status ?? null,
      recorded_values: rvs,
      recordedValues: rvs,
    };
  };

  const normEvent = (e: any): ReplayEvent => {
    const recorded = (e.recorded_values || e.recordedValues || []).map(normRecordedValue);
    return {
      sequence: e.sequence ?? 0,
      event_id: e.event_id || e.eventId || '',
      eventId: e.eventId || e.event_id || '',
      timestamp: e.timestamp || '',
      relative_seconds: e.relative_seconds ?? e.relativeSeconds ?? 0,
      relativeSeconds: e.relativeSeconds ?? e.relative_seconds ?? 0,
      asset_id: e.asset_id || e.assetId || '',
      assetId: e.assetId || e.asset_id || '',
      title: e.title || '',
      event_type: e.event_type || e.eventType || '',
      eventType: e.eventType || e.event_type || '',
      severity: e.severity || '',
      phase: e.phase || 'UNCLASSIFIED',
      description: e.description || '',
      evidence: (e.evidence || []).map(normEvidenceRef),
      related_assets: e.related_assets || e.relatedAssets || [],
      relatedAssets: e.relatedAssets || e.related_assets || [],
      graph_relationships: (e.graph_relationships || e.graphRelationships || []).map(normRelationship),
      graphRelationships: (e.graphRelationships || e.graph_relationships || []).map(normRelationship),
      asset_state: normAssetState(e.asset_state || e.assetState),
      assetState: normAssetState(e.assetState || e.asset_state),
      recorded_values: recorded,
      recordedValues: recorded,
    };
  };

  const sum = data.summary || {};
  const wf = data.window_filter || data.windowFilter;

  return {
    incident_id: data.incident_id || data.incidentId || '',
    incidentId: data.incidentId || data.incident_id || '',
    start_timestamp: data.start_timestamp ?? data.startTimestamp ?? null,
    startTimestamp: data.startTimestamp ?? data.start_timestamp ?? null,
    end_timestamp: data.end_timestamp ?? data.endTimestamp ?? null,
    endTimestamp: data.endTimestamp ?? data.end_timestamp ?? null,
    duration_seconds: data.duration_seconds ?? data.durationSeconds ?? 0,
    durationSeconds: data.durationSeconds ?? data.duration_seconds ?? 0,
    summary: {
      event_count: sum.event_count ?? sum.eventCount ?? 0,
      eventCount: sum.eventCount ?? sum.event_count ?? 0,
      asset_count: sum.asset_count ?? sum.assetCount ?? 0,
      assetCount: sum.assetCount ?? sum.asset_count ?? 0,
      evidence_count: sum.evidence_count ?? sum.evidenceCount ?? 0,
      evidenceCount: sum.evidenceCount ?? sum.evidence_count ?? 0,
      duration_seconds: sum.duration_seconds ?? sum.durationSeconds ?? 0,
      durationSeconds: sum.durationSeconds ?? sum.duration_seconds ?? 0,
    },
    events: (data.events || []).map(normEvent),
    window_filter: wf ? {
      start_offset_seconds: wf.start_offset_seconds ?? wf.startOffsetSeconds ?? null,
      startOffsetSeconds: wf.startOffsetSeconds ?? wf.start_offset_seconds ?? null,
      end_offset_seconds: wf.end_offset_seconds ?? wf.endOffsetSeconds ?? null,
      endOffsetSeconds: wf.endOffsetSeconds ?? wf.end_offset_seconds ?? null,
    } : null,
    windowFilter: wf ? {
      start_offset_seconds: wf.start_offset_seconds ?? wf.startOffsetSeconds ?? null,
      startOffsetSeconds: wf.startOffsetSeconds ?? wf.start_offset_seconds ?? null,
      end_offset_seconds: wf.end_offset_seconds ?? wf.endOffsetSeconds ?? null,
      endOffsetSeconds: wf.endOffsetSeconds ?? wf.end_offset_seconds ?? null,
    } : null,
  };
}


