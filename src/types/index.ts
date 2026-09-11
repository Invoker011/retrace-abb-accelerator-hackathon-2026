export type SeverityLevel = 'Critical' | 'High' | 'Medium' | 'Low';
export type IncidentStatus = 'Under Investigation' | 'Triaged' | 'Resolved' | 'Closed';

export interface Incident {
  id: string;
  title: string;
  plantArea: string;
  severity: SeverityLevel;
  status: IncidentStatus;
  date: string;
  startedAt: string;
  resolvedAt?: string;
  summary: string;
  leadInvestigator: string;
  unresolvedQuestionsCount: number;
}

export type AssetOperationalStatus = 'Normal' | 'Warning' | 'Tripped' | 'Offline';

export interface Asset {
  id: string;
  name: string;
  tag: string;
  type: string;
  plantArea: string;
  status: AssetOperationalStatus;
  manufacturer?: string;
  model?: string;
  criticality: 'Critical' | 'High' | 'Medium' | 'Low';
  specs: Record<string, string>;
  description: string;
}

export type RelationType = 'powers' | 'drives' | 'monitored by' | 'supplies' | 'controls';

export interface AssetRelationship {
  id: string;
  sourceAssetId: string;
  targetAssetId: string;
  relationType: RelationType;
  description: string;
}

export type EventType = 'warning' | 'deviation' | 'disturbance' | 'observation' | 'alarm' | 'normal';

export interface IncidentEvent {
  id: string;
  incidentId: string;
  timestamp: string; // ISO or normalized
  displayTime: string; // e.g. "10:14:01"
  relativeSeconds: number; // offset from incident start
  assetId: string;
  assetName: string;
  eventType: EventType;
  title: string;
  description: string;
  evidenceId: string;
  evidenceRef: string;
  severity: SeverityLevel;
  telemetrySnapshot?: {
    currentA?: number;
    voltageV?: number;
    frequencyHz?: number;
    rpm?: number;
    pressureBar?: number;
    vibrationMmS?: number;
    alarmCode?: string;
  };
}

export type EvidenceCategory =
  | 'PLC / SCADA'
  | 'VFD / Drive Logs'
  | 'Historian Data'
  | 'Engineering Documents'
  | 'Maintenance / Inspection Records'
  | 'Technician Notes & Photos';

export interface Evidence {
  id: string;
  filename: string;
  source: string;
  sourceType: EvidenceCategory;
  timestamp: string;
  normalizedTimestamp: string;
  assetId: string;
  assetName: string;
  extractedEvent: string;
  confidence: number; // 0 - 100
  originalEvidenceRef: string;
  fileSize: string;
  format: 'csv' | 'pdf' | 'text' | 'image';
  previewRows?: Array<Record<string, string | number>>;
  rawContent?: string;
}

export type FindingCategory = 'OBSERVED' | 'CORRELATED' | 'HYPOTHESIS' | 'UNKNOWN';

export interface Finding {
  id: string;
  incidentId: string;
  category: FindingCategory;
  statement: string;
  supportingEvidenceIds: string[];
  relatedAssetIds: string[];
  confidenceScore?: number;
  notes?: string;
}

export interface ChatMessage {
  id: string;
  sender: 'technician' | 'retrace' | 'system';
  content: string;
  timestamp: string;
  supportingEvidence?: Array<{
    id: string;
    filename: string;
    sourceType: EvidenceCategory;
    summary: string;
  }>;
  findingReferenceCategory?: FindingCategory;
  suggestedFollowUps?: string[];
}

export interface PreventionNode {
  step: number;
  title: string;
  assetId?: string;
  assetName?: string;
  timeOffset: string;
  status: 'critical_path' | 'intervention_point' | 'mitigation_outcome' | 'normal';
  description: string;
  safeguardType?: string;
}

export interface PreventionScenario {
  incidentId: string;
  actualPath: PreventionNode[];
  interventionPath: PreventionNode[];
  disclaimer: string;
  safeguards: Array<{
    title: string;
    category: 'Telemetry Detection' | 'Inspection Protocol' | 'Automated Interlock' | 'Operational Procedure';
    status: 'Failed' | 'Late' | 'Recommended Intervention';
    recommendation: string;
  }>;
}

export interface UploadedEvidenceItem {
  evidenceId: string;
  incidentId: string;
  sourceType: EvidenceCategory | string;
  originalFilename: string;
  storedFilename: string;
  contentType: string;
  fileSize: number;
  assetId?: string | null;
  description?: string | null;
  storageUri: string;
  uploadedAt: string;
  processingStatus: string;
  sha256Hash: string;
  metadata?: Record<string, any>;
}

export interface HybridEvidenceResult {
  rank: number;
  retrieval_score: number;
  retrieval_channels: string[];
  semantic_rank?: number | null;
  similarity_score?: number | null;
  keyword_rank?: number | null;
  keyword_score?: number | null;
  evidence_id: string;
  chunk_id: string;
  asset_id?: string | null;
  filename: string;
  source_type: string;
  text: string;
  timestamp?: string | null;
  provenance: Record<string, any>;
}

export interface HybridSearchRequest {
  query: string;
  top_k?: number;
  asset_id?: string | null;
  source_type?: string | null;
}

export interface HybridTemporalContextItem {
  event_id: string;
  timestamp: string;
  relative_seconds?: number | null;
  asset_id: string;
  title: string;
  event_type: string;
  severity: string;
  evidence_id?: string | null;
}

export interface HybridSearchResponse {
  incident_id: string;
  query: string;
  recognized_identifiers: string[];
  evidence: HybridEvidenceResult[];
  graph_context: {
    assets: Array<{
      id: string;
      name: string;
      type: string;
      criticality?: string;
      status?: string;
    }>;
    relationships: Array<{
      source: string;
      target: string;
      relationship: string;
      description?: string;
    }>;
  };
  temporal_context: HybridTemporalContextItem[];
}

export type ReplayPhase =
  | 'PRECURSOR'
  | 'DEGRADATION'
  | 'OPERATOR_OBSERVATION'
  | 'PROTECTIVE_SHUTDOWN'
  | 'UNCLASSIFIED';

export interface ReplayEvidenceReference {
  evidence_id: string;
  filename: string;
  source_type: string;
  asset_id?: string | null;
  timestamp?: string | null;
  original_reference?: string | null;
}

export interface ReplayRecordedValue {
  name: string;
  value: any;
  unit?: string | null;
  source_evidence_id?: string | null;
}

export interface ReplayRelationshipContext {
  source: string;
  relationship: string;
  target: string;
  description?: string | null;
}

export interface ReplayAssetState {
  asset_id: string;
  asset_name?: string | null;
  operational_status?: string | null;
  recorded_values: ReplayRecordedValue[];
}

export interface ReplayEvent {
  sequence: number;
  event_id: string;
  timestamp: string;
  relative_seconds: number;
  asset_id: string;
  title: string;
  event_type: string;
  severity: string;
  phase: ReplayPhase;
  description: string;
  evidence: ReplayEvidenceReference[];
  related_assets: string[];
  graph_relationships: ReplayRelationshipContext[];
  asset_state?: ReplayAssetState | null;
  recorded_values: ReplayRecordedValue[];
}

export interface ReplaySummary {
  event_count: number;
  asset_count: number;
  evidence_count: number;
  duration_seconds: number;
}

export interface ReplayWindowFilter {
  start_offset_seconds?: number | null;
  end_offset_seconds?: number | null;
}

export interface IncidentReplayResponse {
  incident_id: string;
  start_timestamp?: string | null;
  end_timestamp?: string | null;
  duration_seconds: number;
  summary: ReplaySummary;
  events: ReplayEvent[];
  window_filter?: ReplayWindowFilter | null;
}



