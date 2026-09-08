import React, { useState } from 'react';
import {
  Incident,
  Asset,
  AssetRelationship,
  IncidentEvent,
  Evidence,
  Finding,
} from '../../types';
import { FindingBadge } from '../common/FindingBadge';
import { EvidenceBadge } from '../common/EvidenceBadge';
import {
  AlertTriangle,
  Clock,
  MapPin,
  Cpu,
  FileSpreadsheet,
  CheckCircle2,
  Calendar,
  Layers,
  ArrowRight,
  ExternalLink,
  Info,
  Play,
  Network,
} from 'lucide-react';

interface IncidentDetailViewProps {
  incident: Incident;
  assets: Asset[];
  relationships: AssetRelationship[];
  events: IncidentEvent[];
  evidenceList: Evidence[];
  findings: Finding[];
  onSelectEvidence: (evidence: Evidence) => void;
  onNavigate: (view: any) => void;
}

export const IncidentDetailView: React.FC<IncidentDetailViewProps> = ({
  incident,
  assets,
  relationships,
  events,
  evidenceList,
  findings,
  onSelectEvidence,
  onNavigate,
}) => {
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>('P-204');
  const [findingFilter, setFindingFilter] = useState<string>('ALL');

  const filteredFindings =
    findingFilter === 'ALL'
      ? findings
      : findings.filter((f) => f.category === findingFilter);

  const selectedAsset = assets.find((a) => a.id === selectedAssetId) || assets[2];

  return (
    <div id="incident-detail-view" className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* A. Incident Summary Header */}
      <div className="rounded-xl border border-slate-800 bg-[#0a101e] p-6 space-y-4 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2 font-mono text-xs">
              <span className="px-2.5 py-0.5 rounded bg-cyan-950/80 border border-cyan-800 text-cyan-300 font-bold">
                INCIDENT ID: {incident.id}
              </span>
              <span className="px-2.5 py-0.5 rounded bg-rose-950/60 border border-rose-800 text-rose-300 font-semibold">
                SEVERITY: {incident.severity}
              </span>
              <span className="px-2.5 py-0.5 rounded bg-amber-950/50 border border-amber-800 text-amber-300 font-mono">
                STATUS: {incident.status}
              </span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-400 flex items-center gap-1 font-mono">
                <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                {incident.plantArea}
              </span>
              <span className="text-slate-400 flex items-center gap-1 font-mono">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                {incident.date}
              </span>
            </div>
            <h1 className="text-2xl font-bold font-mono text-white tracking-tight">
              {incident.title}
            </h1>
            <p className="text-sm text-slate-300 mt-2 max-w-4xl leading-relaxed">
              {incident.summary}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => onNavigate('replay')}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-semibold shadow-lg shadow-cyan-950/50 transition-all"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Launch Incident Replay</span>
            </button>
            <button
              onClick={() => onNavigate('graph')}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs font-semibold border border-slate-700 transition-colors"
            >
              <Network className="w-3.5 h-3.5 text-blue-400" />
              <span>Context Graph</span>
            </button>
          </div>
        </div>

        {/* Investigator Meta */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-xs pt-1">
          <div>
            <span className="text-slate-500 block mb-0.5">Lead Investigator</span>
            <span className="text-slate-200 font-medium">{incident.leadInvestigator}</span>
          </div>
          <div>
            <span className="text-slate-500 block mb-0.5">Incident Origin Time (T₀)</span>
            <span className="text-cyan-400 font-medium">10:14:01 (27s cascade)</span>
          </div>
          <div>
            <span className="text-slate-500 block mb-0.5">Impacted Process Skid</span>
            <span className="text-slate-200">Chemical Feed Skid B</span>
          </div>
          <div>
            <span className="text-slate-500 block mb-0.5">Investigation Mode</span>
            <span className="text-emerald-400 font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Evidence Grounded
            </span>
          </div>
        </div>
      </div>

      {/* Grid: B. Timeline & C. Assets Involved */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* B. Timeline (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-white">
                Reconstructed Timeline
              </h2>
            </div>
            <span className="text-xs font-mono text-slate-500">
              5 Key Sequenced Events
            </span>
          </div>

          <div className="space-y-3">
            {events.map((evt) => {
              const matchedEvidence = evidenceList.find((e) => e.id === evt.evidenceId);
              return (
                <div
                  key={evt.id}
                  className="p-4 rounded-xl bg-[#0a0f1c] border border-slate-800/90 hover:border-slate-700 transition-all space-y-2.5"
                >
                  <div className="flex items-center justify-between font-mono text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-cyan-300 text-sm px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/60">
                        {evt.displayTime}
                      </span>
                      <span className="text-[11px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-800">
                        +{evt.relativeSeconds}s
                      </span>
                      <span className="font-semibold text-slate-200">
                        {evt.assetName}
                      </span>
                    </div>

                    <span
                      className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded font-bold ${
                        evt.severity === 'Critical'
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : evt.severity === 'High'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800'
                          : 'bg-blue-950 text-blue-300 border border-blue-800'
                      }`}
                    >
                      {evt.severity}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-mono text-xs font-bold text-white">
                      {evt.title}
                    </h3>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                      {evt.description}
                    </p>
                  </div>

                  {/* Telemetry Snapshot Pill if present */}
                  {evt.telemetrySnapshot && (
                    <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-[11px] text-slate-400">
                      {evt.telemetrySnapshot.currentA !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-black/40 border border-slate-800 text-cyan-300">
                          Current: {evt.telemetrySnapshot.currentA} A
                        </span>
                      )}
                      {evt.telemetrySnapshot.pressureBar !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-black/40 border border-slate-800 text-amber-300">
                          Pressure: {evt.telemetrySnapshot.pressureBar} bar
                        </span>
                      )}
                      {evt.telemetrySnapshot.vibrationMmS !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-black/40 border border-slate-800 text-rose-300">
                          Vib: {evt.telemetrySnapshot.vibrationMmS} mm/s
                        </span>
                      )}
                      {evt.telemetrySnapshot.alarmCode && (
                        <span className="px-2 py-0.5 rounded bg-rose-950/60 border border-rose-800 text-rose-300">
                          Code: {evt.telemetrySnapshot.alarmCode}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Supporting Evidence link */}
                  <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-500 truncate max-w-[280px]">
                      Ref: {evt.evidenceRef}
                    </span>
                    {matchedEvidence && (
                      <button
                        onClick={() => onSelectEvidence(matchedEvidence)}
                        className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium hover:underline text-[11px]"
                      >
                        <FileSpreadsheet className="w-3 h-3" />
                        <span>Inspect Source</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* C. Assets Involved (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-400" />
              <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-white">
                Coupled Assets
              </h2>
            </div>
            <span className="text-xs font-mono text-slate-500">
              4 Assets in Topology
            </span>
          </div>

          {/* Asset Selectors */}
          <div className="grid grid-cols-2 gap-2 font-mono text-xs">
            {assets.map((asset) => {
              const isSelected = selectedAssetId === asset.id;
              return (
                <button
                  key={asset.id}
                  onClick={() => setSelectedAssetId(asset.id)}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    isSelected
                      ? 'bg-cyan-950/40 border-cyan-600 text-white shadow-md'
                      : 'bg-[#0a0f1c] border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-cyan-300">{asset.tag}</span>
                    <span
                      className={`w-2 h-2 rounded-full ${
                        asset.status === 'Tripped'
                          ? 'bg-rose-500 animate-pulse'
                          : asset.status === 'Warning'
                          ? 'bg-amber-400'
                          : 'bg-emerald-400'
                      }`}
                    />
                  </div>
                  <div className="text-[11px] text-slate-400 truncate">{asset.type}</div>
                </button>
              );
            })}
          </div>

          {/* Selected Asset Deep Dive Card */}
          <div className="p-5 rounded-xl bg-[#090f1d] border border-slate-800 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  {selectedAsset.plantArea}
                </span>
                <h3 className="font-mono text-base font-bold text-white mt-1">
                  {selectedAsset.name}
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  {selectedAsset.description}
                </p>
              </div>
            </div>

            {/* Specs Grid */}
            <div className="p-3.5 rounded-lg bg-black/40 border border-slate-800 space-y-2 font-mono text-xs">
              <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider block">
                Engineering Nameplate Parameters
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                {Object.entries(selectedAsset.specs).map(([key, val]) => (
                  <div key={key}>
                    <span className="text-slate-500 block">{key}:</span>
                    <span className="text-slate-200 font-semibold">{val}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Asset Couplings */}
            <div>
              <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider font-mono block mb-2">
                Physical Topology Couplings
              </span>
              <div className="space-y-1.5 font-mono text-xs">
                {relationships.map((rel) => (
                  <div
                    key={rel.id}
                    className="p-2 rounded bg-slate-900/60 border border-slate-800/80 flex items-center justify-between text-[11px]"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="text-cyan-300 font-bold">{rel.sourceAssetId}</span>
                      <span className="text-slate-400 font-sans italic text-[10px]">
                        {rel.relationType} →
                      </span>
                      <span className="text-white font-bold">{rel.targetAssetId}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* E. Findings Panel (OBSERVED, CORRELATED, HYPOTHESIS, UNKNOWN) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
          <div>
            <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Validated Incident Findings
            </h2>
            <p className="text-xs text-slate-400 font-sans">
              Strictly segregated into Observed (empirical), Correlated (topology/timing), Hypothesis (plausible), and Unknown (gaps).
            </p>
          </div>

          {/* Category Filter Tabs */}
          <div className="flex items-center gap-1 font-mono text-xs">
            {['ALL', 'OBSERVED', 'CORRELATED', 'HYPOTHESIS', 'UNKNOWN'].map((cat) => (
              <button
                key={cat}
                onClick={() => setFindingFilter(cat)}
                className={`px-2.5 py-1 rounded transition-colors ${
                  findingFilter === cat
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredFindings.map((finding) => (
            <div
              key={finding.id}
              className="p-5 rounded-xl bg-[#0a0f1d] border border-slate-800/90 flex flex-col justify-between space-y-3"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <FindingBadge category={finding.category} />
                  <span className="text-[10px] font-mono text-slate-500">
                    ID: {finding.id}
                  </span>
                </div>
                <p className="text-sm font-medium text-slate-100 leading-relaxed font-sans">
                  {finding.statement}
                </p>
                {finding.notes && (
                  <p className="text-xs text-slate-400 mt-2 font-mono leading-relaxed bg-black/30 p-2 rounded border border-slate-800/60">
                    {finding.notes}
                  </p>
                )}
              </div>

              {/* Supporting Evidence Chips */}
              <div className="pt-3 border-t border-slate-800/70 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                <span className="text-slate-500 text-[11px]">Supporting Evidence:</span>
                <div className="flex flex-wrap items-center gap-1.5">
                  {finding.supportingEvidenceIds.length === 0 ? (
                    <span className="text-amber-400 text-[11px] italic">
                      None (Physical inspection pending)
                    </span>
                  ) : (
                    finding.supportingEvidenceIds.map((evId) => {
                      const ev = evidenceList.find((e) => e.id === evId);
                      return ev ? (
                        <button
                          key={evId}
                          onClick={() => onSelectEvidence(ev)}
                          className="px-2 py-0.5 rounded bg-slate-800 hover:bg-cyan-950 text-cyan-300 hover:border-cyan-700 border border-slate-700 text-[11px] transition-colors"
                        >
                          {ev.filename}
                        </button>
                      ) : null;
                    })
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* D. Evidence Panel (6 Sources) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div>
            <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-cyan-400" />
              Evidence Repository (6 Sources)
            </h2>
            <p className="text-xs text-slate-400 font-sans">
              Click any evidence record to open the detailed provenance viewer and telemetry audit logs.
            </p>
          </div>
          <button
            onClick={() => onNavigate('evidence')}
            className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1"
          >
            <span>Full Evidence Workspace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {evidenceList.map((ev) => (
            <div
              key={ev.id}
              onClick={() => onSelectEvidence(ev)}
              className="p-4 rounded-xl bg-[#0a0f1d] border border-slate-800 hover:border-cyan-800/60 transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <EvidenceBadge category={ev.sourceType} size="sm" />
                  <span className="text-[10px] font-mono text-slate-500">{ev.fileSize}</span>
                </div>
                <h4 className="font-mono text-xs font-bold text-white group-hover:text-cyan-300 transition-colors">
                  {ev.filename}
                </h4>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                  {ev.extractedEvent}
                </p>
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>Asset: {ev.assetId}</span>
                <span className="text-cyan-400 group-hover:underline flex items-center gap-1">
                  <span>Inspect</span>
                  <ExternalLink className="w-3 h-3" />
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
