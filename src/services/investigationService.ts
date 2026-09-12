import {
  mockChatConversation,
  mockPreventionScenario,
  mockEvidence,
} from '../data/mockData';
import { ChatMessage, PreventionScenario, FindingCategory, EvidenceCategory } from '../types';
import { apiClient } from './apiClient';

/**
 * Investigation Service
 * Decision-support conversational assistant and counterfactual prevention simulator.
 * Queries FastAPI backend endpoints (/api/investigation/query & /api/incidents/.../prevention)
 * with graceful fallback to deterministic local intelligence if backend is unreachable.
 */
export const investigationService = {
  async getInitialConversation(incidentId: string): Promise<ChatMessage[]> {
    return [];
  },

  async getSuggestedQuestions(): Promise<string[]> {
    return [
      'Why did Pump P-204 shut down?',
      'What happened before the shutdown?',
      'Which assets were involved?',
      'What evidence supports this finding?',
      'What should the technician inspect next?',
      'What information is still missing?',
    ];
  },

  async getPreventionScenario(incidentId: string): Promise<PreventionScenario> {
    try {
      const data = await apiClient.get<any>(`/api/incidents/${incidentId}/prevention`);
      if (data && (data.actual_path || data.actualPath)) {
        return {
          incidentId: data.incidentId || data.incident_id || incidentId,
          disclaimer:
            data.disclaimer ||
            'This is an exploratory prevention scenario. RETRACE does not claim that the proposed intervention would definitely have prevented the incident.',
          actualPath: (data.actualPath || data.actual_path || []).map((node: any) => ({
            step: node.step,
            title: node.title,
            assetId: node.assetId || node.asset_id,
            assetName: node.assetName || node.asset_name,
            timeOffset: node.timeOffset || node.time_offset,
            status: node.status,
            description: node.description,
            safeguardType: node.safeguardType || node.safeguard_type,
          })),
          interventionPath: (
            data.interventionPath ||
            data.possible_intervention_path ||
            data.possibleInterventionPath ||
            []
          ).map((node: any) => ({
            step: node.step,
            title: node.title,
            assetId: node.assetId || node.asset_id,
            assetName: node.assetName || node.asset_name,
            timeOffset: node.timeOffset || node.time_offset,
            status: node.status,
            description: node.description,
            safeguardType: node.safeguardType || node.safeguard_type,
          })),
          safeguards: data.safeguards || [],
        };
      }
    } catch {
      // Fallback
    }
    return { ...mockPreventionScenario };
  },

  async queryInvestigation(
    incidentId: string,
    question: string
  ): Promise<ChatMessage> {
    // Attempt Grounded Investigation Reasoning endpoint first
    try {
      const groundedRes = await apiClient.post<any>(`/api/incidents/${incidentId}/investigate`, {
        query: question,
        top_k: 8,
      });

      if (groundedRes && (groundedRes.summary || (groundedRes.findings && groundedRes.findings.length > 0))) {
        const lines: string[] = [];
        if (groundedRes.summary) {
          lines.push(groundedRes.summary);
        }

        if (Array.isArray(groundedRes.findings) && groundedRes.findings.length > 0) {
          lines.push('\n**Evidence-Grounded Findings:**');
          groundedRes.findings.forEach((f: any) => {
            const classLabel = f.classification || 'CORRELATED';
            const citations = [
              ...(f.evidence_ids || []).map((id: string) => `[${id}]`),
              ...(f.event_ids || []).map((id: string) => `[${id}]`),
              ...(f.asset_ids || []).map((id: string) => `@${id}`),
            ].join(' ');
            lines.push(`• **${classLabel}**: ${f.statement}${citations ? ` ${citations}` : ''}`);
            if (f.basis) {
              lines.push(`   _Basis_: ${f.basis}`);
            }
          });
        }

        if (Array.isArray(groundedRes.unknowns) && groundedRes.unknowns.length > 0) {
          lines.push('\n**Identified Evidence Gaps (Unknown):**');
          groundedRes.unknowns.forEach((u: string) => {
            lines.push(`• ${u}`);
          });
        }

        if (Array.isArray(groundedRes.recommended_checks) && groundedRes.recommended_checks.length > 0) {
          lines.push('\n**Advisory Diagnostic Checks (Human Review Required):**');
          groundedRes.recommended_checks.forEach((c: any) => {
            lines.push(`• ${c.check} (Reason: ${c.reason})`);
          });
        }

        const supportingEv = (groundedRes.sources_used || []).map((s: any) => ({
          id: s.evidence_id || s.id,
          filename: s.filename || 'Evidence Record',
          sourceType: (s.source_type || s.sourceType || 'Historian and Time-Series Data') as EvidenceCategory,
          summary: `${s.asset_id ? `Asset: ${s.asset_id}. ` : ''}${s.timestamp ? `Time: ${s.timestamp}. ` : ''}${s.original_reference ? `Ref: ${s.original_reference}` : ''}`.trim(),
        }));

        let dominantCategory: FindingCategory = 'CORRELATED';
        if (groundedRes.findings && groundedRes.findings.length > 0) {
          dominantCategory = groundedRes.findings[0].classification as FindingCategory;
        }

        return {
          id: `MSG-${Date.now()}`,
          sender: 'retrace',
          content: lines.join('\n'),
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          supportingEvidence: supportingEv.length > 0 ? supportingEv : undefined,
          findingReferenceCategory: dominantCategory,
          suggestedFollowUps: [
            'What happened before the shutdown?',
            'Which assets were involved?',
            'What evidence supports this finding?',
            'What should the technician inspect next?',
            'What information is still missing?',
          ],
        };
      }
    } catch {
      // Fall through to query endpoint or local intelligence
    }

    // Attempt FastAPI backend query endpoint
    try {
      const apiRes = await apiClient.post<any>('/api/investigation/query', {
        incident_id: incidentId,
        question: question,
      });

      if (apiRes && apiRes.answer) {
        const supportingEv = (
          apiRes.supporting_evidence ||
          apiRes.supportingEvidence ||
          []
        ).map((e: any) => ({
          id: e.id,
          filename: e.filename,
          sourceType: (e.sourceType || e.source_type) as EvidenceCategory,
          summary: e.summary || e.extracted_content || e.extractedEvent || '',
        }));

        const resultMsg: ChatMessage = {
          id: `MSG-${Date.now()}`,
          sender: 'retrace',
          content: apiRes.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          supportingEvidence: supportingEv.length > 0 ? supportingEv : undefined,
          findingReferenceCategory: apiRes.classification as FindingCategory,
          suggestedFollowUps: apiRes.suggested_follow_ups || apiRes.suggestedFollowUps || [
            'What happened before the shutdown?',
            'Which assets were involved?',
            'What evidence supports this finding?',
            'What should the technician inspect next?',
            'What information is still missing?',
          ],
        };
        return resultMsg;
      }
    } catch {
      // Offline / Network fallback to local deterministic logic
    }

    // Local deterministic fallback
    const qLower = question.toLowerCase();

    let replyContent = '';
    let category: FindingCategory = 'CORRELATED';
    let supportingIds: string[] = [];
    const followUps: string[] = [
      'What evidence supports this finding?',
      'What should the technician inspect next?',
      'What information is still missing?',
    ];

    if (qLower.includes('before the shutdown') || qLower.includes('happened before')) {
      category = 'OBSERVED';
      supportingIds = ['EVD-001', 'EVD-003'];
      replyContent =
        'Sequence reconstructed from drive logs and historian:\n\n' +
        '1. 10:14:01 — VFD-204 recorded an overcurrent warning (268.4A peak) at the inverter output stage.\n' +
        '2. 10:14:05 — Motor M-204 experienced an 8.2% phase current imbalance.\n' +
        '3. 10:14:12 — Pump P-204 discharge pressure dropped precipitously from 6.8 bar to 4.2 bar.\n' +
        '4. 10:14:18 — Operator J. Miller logged audible cavitation screech and baseplate vibration.\n\n' +
        'All early warning milestones occurred within a 27-second window before the trip alarm.';
    } else if (qLower.includes('which assets') || qLower.includes('assets were involved')) {
      category = 'CORRELATED';
      supportingIds = ['EVD-001', 'EVD-003', 'EVD-002'];
      replyContent =
        'Four key assets are in the direct mechanical and electrical power train:\n\n' +
        '• VFD-204 (Variable Frequency Drive): powers Motor M-204.\n' +
        '• Motor M-204 (110kW Induction Motor): drives Pump P-204.\n' +
        '• Pump P-204 (Centrifugal Booster Pump): monitored by PLC-204.\n' +
        '• PLC-204 (Safety & Process Controller): executed the hard trip interlock.';
    } else if (qLower.includes('inspect next') || qLower.includes('what should the technician inspect')) {
      category = 'HYPOTHESIS';
      supportingIds = ['EVD-004', 'EVD-005', 'EVD-006'];
      replyContent =
        'Recommended Human Engineering & Physical Inspection Steps:\n\n' +
        '1. Suction Strainer ST-204: Inspect for partial blockage, debris, or restriction causing low suction head (NPSHa deficit).\n' +
        '2. Flexible Disc Coupling: Verify whether the +0.08mm angular offset reported in WO-88492 exacerbated torsional vibration under load.\n' +
        '3. Pump Impeller & Casing: Inspect for cavitation pitting or mechanical binding.\n\n' +
        '⚠️ Safety Notice: RETRACE is advisory only. Ensure Lock-Out / Tag-Out (LOTO) protocols are executed prior to physical intervention.';
    } else if (qLower.includes('missing') || qLower.includes('information is still missing')) {
      category = 'UNKNOWN';
      supportingIds = [];
      replyContent =
        'Current Evidence Gaps (Unknown):\n\n' +
        '• High-frequency spectral FFT vibration data during the 10:14:01 overcurrent pulse is currently missing (historian recorded 1-second RMS averages only).\n' +
        '• Physical condition of the pump impeller and suction basket has not yet been visually confirmed.\n' +
        '• Drive DC bus ripple voltage telemetry during the initial 480ms spike has not been downloaded from inverter internal trace.';
    } else if (qLower.includes('evidence supports') || qLower.includes('what evidence')) {
      category = 'OBSERVED';
      supportingIds = ['EVD-001', 'EVD-002', 'EVD-003', 'EVD-006'];
      replyContent =
        'The investigation findings are grounded in six multi-modal evidence artifacts:\n\n' +
        '• VFD_204_Log.csv: Hardware-stamped overcurrent warning W-2310 (Row 4209).\n' +
        '• SCADA_Alarm_Log.csv: Alarm Seq #88310 vibration trip interlock execution.\n' +
        '• Historian_P204.csv: Synchronized 1-second process head/flow/motor kW trace.\n' +
        '• Technician_Observation_001: Independent human operator confirmation of audible screech and baseplate shaking at 10:14:18.';
    } else {
      category = 'CORRELATED';
      supportingIds = ['EVD-001', 'EVD-003', 'EVD-002'];
      replyContent =
        `Based on the ingested operational telemetry, VFD-204 registered an overcurrent pulse at 10:14:01, followed sequentially by Motor M-204 phase divergence, Pump P-204 cavitation disturbance, and PLC-204 trip at 10:14:28.\n\n` +
        `This chain is correlated by physical asset topology and synchronized timestamps, but physical teardown is required to confirm whether the root trigger was mechanical blockage or electrical transient.`;
    }

    const matchedEvidence = mockEvidence
      .filter((e) => supportingIds.includes(e.id))
      .map((e) => ({
        id: e.id,
        filename: e.filename,
        sourceType: e.sourceType,
        summary: e.extractedEvent,
      }));

    const responseMsg: ChatMessage = {
      id: `MSG-${Date.now()}`,
      sender: 'retrace',
      content: replyContent,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      supportingEvidence: matchedEvidence.length > 0 ? matchedEvidence : undefined,
      findingReferenceCategory: category,
      suggestedFollowUps: followUps,
    };

    return responseMsg;
  },
};

