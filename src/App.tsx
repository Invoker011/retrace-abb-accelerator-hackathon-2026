import React, { useState, useEffect } from 'react';
import { NavView, Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { DashboardView } from './components/dashboard/DashboardView';
import { IncidentDetailView } from './components/incidents/IncidentDetailView';
import { InvestigationChatView } from './components/investigation/InvestigationChatView';
import { IncidentReplayView } from './components/replay/IncidentReplayView';
import { ContextGraphView } from './components/graph/ContextGraphView';
import { EvidenceView } from './components/evidence/EvidenceView';
import { PreventionView } from './components/prevention/PreventionView';
import { EvidenceModal } from './components/evidence/EvidenceModal';

import { incidentService } from './services/incidentService';
import { evidenceService } from './services/evidenceService';
import { investigationService } from './services/investigationService';

import {
  Incident,
  Asset,
  AssetRelationship,
  IncidentEvent,
  Evidence,
  Finding,
  PreventionScenario,
} from './types';

export default function App() {
  const [activeView, setActiveView] = useState<NavView>('dashboard');
  const [incident, setIncident] = useState<Incident | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [relationships, setRelationships] = useState<AssetRelationship[]>([]);
  const [events, setEvents] = useState<IncidentEvent[]>([]);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [preventionScenario, setPreventionScenario] = useState<PreventionScenario | null>(null);

  // Evidence modal inspection state
  const [modalEvidence, setModalEvidence] = useState<Evidence | null>(null);
  // Selected evidence inside the dedicated evidence view
  const [selectedEvidenceView, setSelectedEvidenceView] = useState<Evidence | null>(null);

  // Load initial synthetic data from service layer
  useEffect(() => {
    async function loadData() {
      const inc = await incidentService.getIncidentById('INC-2026-001');
      if (inc) setIncident(inc);

      const asts = await incidentService.getIncidentAssets();
      setAssets(asts);

      const rels = await incidentService.getAssetRelationships();
      setRelationships(rels);

      const evts = await incidentService.getIncidentTimeline('INC-2026-001');
      setEvents(evts);

      const evd = await evidenceService.getEvidenceList();
      setEvidenceList(evd);
      if (evd.length > 0) setSelectedEvidenceView(evd[0]);

      const fnds = await incidentService.getIncidentFindings('INC-2026-001');
      setFindings(fnds);

      const prev = await investigationService.getPreventionScenario('INC-2026-001');
      setPreventionScenario(prev);
    }

    loadData();
  }, []);

  const handleOpenEvidenceModal = (evidence: Evidence) => {
    setModalEvidence(evidence);
  };

  const handleSelectEvidenceForView = (evidence: Evidence) => {
    setSelectedEvidenceView(evidence);
    setModalEvidence(evidence);
  };

  if (!incident || !preventionScenario) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#070a11] text-slate-400 font-mono text-xs">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span>Initializing RETRACE Industrial Intelligence Engine...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[#070a11] text-slate-100 font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* 1. Left Navigation Sidebar */}
      <Sidebar
        activeView={activeView}
        onNavigate={setActiveView}
        activeIncidentId={incident.id}
      />

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <Header
          currentIncident={incident}
          onNavigateToView={(v) => setActiveView(v as NavView)}
        />

        {/* View Switcher Container */}
        <main className="flex-1 overflow-y-auto pb-12">
          {activeView === 'dashboard' && (
            <DashboardView
              incident={incident}
              assets={assets}
              events={events}
              evidenceList={evidenceList}
              findings={findings}
              onNavigate={setActiveView}
              onSelectEvidence={handleOpenEvidenceModal}
            />
          )}

          {activeView === 'incidents' && (
            <IncidentDetailView
              incident={incident}
              assets={assets}
              relationships={relationships}
              events={events}
              evidenceList={evidenceList}
              findings={findings}
              onSelectEvidence={handleOpenEvidenceModal}
              onNavigate={setActiveView}
            />
          )}

          {activeView === 'investigation' && (
            <InvestigationChatView
              evidenceList={evidenceList}
              onSelectEvidence={handleOpenEvidenceModal}
            />
          )}

          {activeView === 'replay' && (
            <IncidentReplayView
              events={events}
              assets={assets}
            />
          )}

          {activeView === 'graph' && (
            <ContextGraphView
              incident={incident}
              assets={assets}
              relationships={relationships}
              evidenceList={evidenceList}
              onSelectEvidence={handleOpenEvidenceModal}
            />
          )}

          {activeView === 'evidence' && (
            <EvidenceView
              evidenceList={evidenceList}
              selectedEvidence={selectedEvidenceView}
              onSelectEvidence={(ev) => {
                setSelectedEvidenceView(ev);
                handleOpenEvidenceModal(ev);
              }}
            />
          )}

          {activeView === 'prevention' && (
            <PreventionView scenario={preventionScenario} />
          )}
        </main>
      </div>

      {/* Global Evidence Inspector Modal */}
      <EvidenceModal
        evidence={modalEvidence}
        onClose={() => setModalEvidence(null)}
      />
    </div>
  );
}
