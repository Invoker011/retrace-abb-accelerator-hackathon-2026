import { apiClient } from './apiClient';

export interface GraphNodeData {
  id: string;
  type: string;
  label: string;
  metadata: Record<string, any>;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  relationship: string;
  metadata: Record<string, any>;
}

export interface GraphResponseData {
  incident_id: string;
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  source: 'neo4j' | 'mock' | string;
}

export interface GraphSyncResult {
  incident_id: string;
  nodes_created_or_matched: number;
  relationships_created_or_matched: number;
  status: string;
}

export interface AssetPathResult {
  incident_id: string;
  source_asset: string;
  target_asset: string;
  found: boolean;
  path: any[];
  relationships: string[];
  length: number;
}

export const graphService = {
  /**
   * Fetches the Incident Context Graph from the Neo4j-backed API endpoint.
   * Falls back gracefully if backend endpoint is unavailable.
   */
  async getIncidentGraph(incidentId: string): Promise<GraphResponseData | null> {
    try {
      const data = await apiClient.get<GraphResponseData>(`/api/incidents/${incidentId}/graph`);
      if (data && Array.isArray(data.nodes) && data.nodes.length > 0) {
        return data;
      }
    } catch {
      // Fallback handled by caller
    }
    return null;
  },

  /**
   * Triggers an idempotent synchronization of incident context entities into Neo4j.
   */
  async syncIncidentGraph(incidentId: string): Promise<GraphSyncResult | null> {
    try {
      return await apiClient.post<GraphSyncResult>(`/api/incidents/${incidentId}/graph/sync`, {});
    } catch {
      return null;
    }
  },

  /**
   * Discovers the equipment topology relationship path between two assets.
   */
  async getAssetPath(
    incidentId: string,
    sourceAsset: string,
    targetAsset: string
  ): Promise<AssetPathResult | null> {
    try {
      return await apiClient.get<AssetPathResult>(
        `/api/incidents/${incidentId}/graph/paths?source_asset=${encodeURIComponent(
          sourceAsset
        )}&target_asset=${encodeURIComponent(targetAsset)}`
      );
    } catch {
      return null;
    }
  },
};
