import { apiClient } from './apiClient';
import {
  PreventionPathsRequest,
  PreventionPathsResponse,
} from '../types';

export const preventionService = {
  /**
   * Request evidence-grounded counterfactual potential prevention paths for an incident.
   */
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
