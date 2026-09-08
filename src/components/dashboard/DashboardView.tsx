import React from 'react';
import {
  Incident,
  Asset,
  IncidentEvent,
  Evidence,
  Finding,
} from '../../types';
import { FindingBadge } from '../common/FindingBadge';
import { EvidenceBadge } from '../common/EvidenceBadge';
import {
  AlertOctagon,
  ArrowRight,
  Clock,
  Layers,
  FileCheck,
  Cpu,
  HelpCircle,
  Play,
  Network,
  ChevronRight,
  ShieldCheck,
  GitFork,
} from 'lucide-react';

interface DashboardViewProps {
  incident: Incident;
  assets: Asset[];
  events: IncidentEvent[];
  evidenceList: Evidence[];
  findings: Finding[];
  onNavigate: (view: any) => void;
  onSelectEvidence: (evidence: Evidence) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  incident,
  assets,
  events,
  evidenceList,
  findings,
  onNavigate,
  onSelectEvidence,
}) => {
  // Findings categorized
  const observedCount = findings.filter((f) => f.category === 'OBSERVED').length;
  const correlatedCount = findings.filter((f) => f.category === 'CORRELATED').length;
  const hypothesisCount = findings.filter((f) => f.category === 'HYPOTHESIS').length;
  const unknownCount = findings.filter((f) => f.category === 'UNKNOWN').length;

  return (
    <div id="dashboard-view" className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Banner / System State */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">
              Multimodal Maintenance Intelligence
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white mt-1">
            Industrial Incident Intelligence Dashboard
          </h1>
          <p className="text-sm text-slate-400 font-sans mt-0.5">
            Real-time reconstruction from fragmented SCADA, VFD drive telemetry, historian series, and field notes.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            id="dash-open-replay-btn"
            onClick={() => onNavigate('replay')}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-semibold shadow-lg shadow-cyan-900/30 transition-all hover:scale-[1.02]"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Launch Replay</span>
          </button>
          <button
            id="dash-open-investigation-btn"
            onClick={() => onNavigate('investigation')}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-mono text-xs font-semibold transition-all hover:scale-[1.02]"
          >
            <span>Troubleshoot Assistant</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 5 Core Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 font-mono">
        {/* Active Incidents */}
        <div className="p-4 rounded-xl bg-[#0b101c] border border-slate-800 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
            <span>Active Incidents</span>
            <AlertOctagon className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-white">01</div>
          <div className="text-[11px] text-rose-400 mt-1 flex items-center gap-1 font-sans">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
            INC-2026-001 (High)
          </div>
        </div>

        {/* Evidence Sources */}
        <div className="p-4 rounded-xl bg-[#0b101c] border border-slate-800 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
            <span>Evidence Sources</span>
            <FileCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400">{evidenceList.length}</div>
          <div className="text-[11px] text-slate-400 mt-1 font-sans">
            Across 6 distinct modalities
          </div>
        </div>

        {/* Assets Involved */}
        <div className="p-4 rounded-xl bg-[#0b101c] border border-slate-800 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
            <span>Assets Involved</span>
            <Cpu className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400">{assets.length}</div>
          <div className="text-[11px] text-slate-400 mt-1 font-sans">
            Coupled Train B cascade
          </div>
        </div>

        {/* Findings */}
        <div className="p-4 rounded-xl bg-[#0b101c] border border-slate-800 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
            <span>Validated Findings</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">{findings.length}</div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1 font-sans">
            <span>{observedCount} Obs • {correlatedCount} Corr • {hypothesisCount} Hyp</span>
          </div>
        </div>

        {/* Unresolved Questions */}
        <div className="p-4 rounded-xl bg-[#0b101c] border border-slate-800 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
            <span>Evidence Gaps</span>
            <HelpCircle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">02</div>
          <div className="text-[11px] text-amber-300/80 mt-1 font-sans">
            Mechanical root unconfirmed
          </div>
        </div>
      </div>

      {/* Featured Incident Spotlight */}
      <div className="rounded-xl border border-slate-800 bg-[#090f1d] overflow-hidden shadow-xl">
        <div className="p-6 border-b border-slate-800 bg-gradient-to-r from-slate-900 to-[#0d1627] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2 font-mono text-xs">
              <span className="px-2.5 py-0.5 rounded bg-rose-950/80 border border-rose-800/80 text-rose-300 font-semibold">
                SEVERITY: {incident.severity}
              </span>
              <span className="px-2.5 py-0.5 rounded bg-amber-950/60 border border-amber-800/60 text-amber-300">
                STATUS: {incident.status}
              </span>
              <span className="text-slate-400">|</span>
              <span className="text-slate-400 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {incident.date} (T₀: 10:14:01)
              </span>
              <span className="text-slate-400">|</span>
              <span className="text-cyan-400">{incident.plantArea}</span>
            </div>
            <h2 className="text-xl font-bold font-mono text-white flex items-center gap-3">
              <span>{incident.id}:</span>
              <span className="text-slate-200">{incident.title}</span>
            </h2>
            <p className="text-sm text-slate-300 mt-2 max-w-3xl leading-relaxed">
              {incident.summary}
            </p>
          </div>

          <button
            id="view-incident-detail-btn"
            onClick={() => onNavigate('incidents')}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-mono text-xs font-medium border border-slate-700 shrink-0 transition-colors"
          >
            <span>Open Incident Workspace</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* 2-Column: Synthetic Timeline Preview & Asset Propagation */}
        <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-800">
          {/* Left Column: Synthetic Timeline */}
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                Reconstructed Chronological Sequence
              </h3>
              <span className="text-[11px] font-mono text-slate-500">27s Total Window</span>
            </div>

            <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
              {events.map((evt, idx) => (
                <div key={evt.id} className="relative group">
                  {/* Timeline dot */}
                  <div
                    className={`absolute -left-[23px] top-1.5 w-3.5 h-3.5 rounded-full border-2 border-[#090f1d] ${
                      evt.severity === 'Critical'
                        ? 'bg-rose-500 ring-2 ring-rose-500/30'
                        : evt.severity === 'High'
                        ? 'bg-amber-400'
                        : 'bg-cyan-400'
                    }`}
                  />
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-mono text-xs font-bold text-cyan-300">
                      {evt.displayTime}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                      +{evt.relativeSeconds}s
                    </span>
                  </div>
                  <div className="font-semibold text-xs text-white mt-0.5">
                    {evt.title}
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5 leading-snug line-clamp-2">
                    {evt.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Right Column: Physical Asset Flow & Findings Snapshot */}
          <div className="p-6 space-y-6">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <GitFork className="w-4 h-4 text-blue-400" />
                  Asset Coupling Chain
                </h3>
                <button
                  onClick={() => onNavigate('graph')}
                  className="text-[11px] font-mono text-cyan-400 hover:underline flex items-center gap-1"
                >
                  <Network className="w-3 h-3" />
                  <span>View Graph</span>
                </button>
              </div>

              {/* Asset Chain Visual */}
              <div className="p-3.5 rounded-lg bg-black/40 border border-slate-800/80 space-y-2.5 font-mono text-xs">
                <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    <span className="font-bold text-slate-200">VFD-204</span>
                  </div>
                  <span className="text-[11px] text-cyan-400 font-sans italic">powers →</span>
                  <span className="text-slate-400 text-[11px]">ACS880 Inverter</span>
                </div>

                <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    <span className="font-bold text-slate-200">Motor M-204</span>
                  </div>
                  <span className="text-[11px] text-cyan-400 font-sans italic">drives →</span>
                  <span className="text-slate-400 text-[11px]">110kW Induction</span>
                </div>

                <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                    <span className="font-bold text-slate-200">Pump P-204</span>
                  </div>
                  <span className="text-[11px] text-cyan-400 font-sans italic">monitored by →</span>
                  <span className="text-slate-400 text-[11px]">Centrifugal Booster</span>
                </div>

                <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="font-bold text-slate-200">PLC-204</span>
                  </div>
                  <span className="text-[11px] text-emerald-400 font-sans">Tripped interlock</span>
                  <span className="text-slate-400 text-[11px]">Safety PLC Rack</span>
                </div>
              </div>
            </div>

            {/* Grounding Categories Snapshot */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                  Current Intelligence Taxonomy
                </h3>
                <span className="text-[10px] font-mono text-slate-500">Strict Categorization</span>
              </div>
              <div className="space-y-2">
                {findings.slice(0, 3).map((finding) => (
                  <div
                    key={finding.id}
                    className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 flex items-start gap-3"
                  >
                    <FindingBadge category={finding.category} size="sm" className="shrink-0 mt-0.5" />
                    <p className="text-xs text-slate-300 leading-snug font-sans">
                      {finding.statement}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Evidence Breakdown Grid (6 Categories) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
              Multimodal Ingestion Evidence Sources
            </h3>
            <p className="text-xs text-slate-400 font-sans">
              All 6 industrial categories ingested and timestamp-aligned for INC-2026-001
            </p>
          </div>
          <button
            onClick={() => onNavigate('evidence')}
            className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1"
          >
            <span>Explore All Evidence</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {evidenceList.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectEvidence(item)}
              className="p-4 rounded-xl bg-[#090e1b] border border-slate-800 hover:border-cyan-800/60 transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <EvidenceBadge category={item.sourceType} size="sm" />
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/50 text-emerald-400 border border-emerald-900/50">
                    {item.confidence}% Grounded
                  </span>
                </div>
                <h4 className="font-mono text-xs font-bold text-slate-200 group-hover:text-cyan-300 transition-colors">
                  {item.filename}
                </h4>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                  {item.extractedEvent}
                </p>
              </div>

              <div className="mt-3 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>Asset: {item.assetId}</span>
                <span className="text-cyan-400 group-hover:translate-x-0.5 transition-transform">
                  Inspect →
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
