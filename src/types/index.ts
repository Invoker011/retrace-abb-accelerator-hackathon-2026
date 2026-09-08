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
