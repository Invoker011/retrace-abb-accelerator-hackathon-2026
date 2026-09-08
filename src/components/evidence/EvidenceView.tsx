import React, { useState } from 'react';
import { Evidence, EvidenceCategory } from '../../types';
import { EvidenceBadge } from '../common/EvidenceBadge';
import {
  Files,
  Search,
  FileSpreadsheet,
  FileCode,
  Database,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Cpu,
  Download,
  Filter,
} from 'lucide-react';

interface EvidenceViewProps {
  evidenceList: Evidence[];
  selectedEvidence: Evidence | null;
  onSelectEvidence: (evidence: Evidence) => void;
}

export const EvidenceView: React.FC<EvidenceViewProps> = ({
  evidenceList,
  selectedEvidence,
  onSelectEvidence,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const activeEvidence = selectedEvidence || evidenceList[0];

  const categories: string[] = [
    'ALL',
    'PLC / SCADA',
    'VFD / Drive Logs',
    'Historian Data',
    'Engineering Documents',
    'Maintenance / Inspection Records',
    'Technician Notes & Photos',
  ];

  const filteredEvidence = evidenceList.filter((item) => {
    const matchesCategory =
      selectedCategory === 'ALL' || item.sourceType === selectedCategory;
    const matchesSearch =
      searchQuery === '' ||
      item.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.extractedEvent.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.assetId.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div id="evidence-view" className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">
              Multimodal Ingestion & Data Provenance
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300 font-mono">
              6 Ingested Modalities
            </span>
          </div>
          <h1 className="text-2xl font-bold font-mono text-white mt-1">
            Industrial Evidence Repository
          </h1>
          <p className="text-xs text-slate-400 font-sans">
            Immutable provenance logs, telemetry extracts, and engineering records for INC-2026-001.
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search artifacts, tags, rows..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
          />
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap items-center gap-1.5 font-mono text-xs">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              selectedCategory === cat
                ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold'
                : 'text-slate-400 hover:text-white bg-slate-900/60 border border-slate-800/80'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Main 2-Column Split: List + Deep Provenance Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Artifact List (5 Cols) */}
        <div className="lg:col-span-5 space-y-3 max-h-[75vh] overflow-y-auto pr-1">
          {filteredEvidence.map((item) => {
            const isSelected = activeEvidence?.id === item.id;
            return (
              <div
                key={item.id}
                onClick={() => onSelectEvidence(item)}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-cyan-950/40 border-cyan-600 shadow-lg shadow-cyan-950/50 ring-1 ring-cyan-500/50'
                    : 'bg-[#0a0f1d] border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <EvidenceBadge category={item.sourceType} size="sm" />
                  <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                    {item.confidence}% Grounded
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {item.format === 'csv' ? (
                    <FileSpreadsheet className="w-4 h-4 text-cyan-400 shrink-0" />
                  ) : item.format === 'pdf' ? (
                    <FileCode className="w-4 h-4 text-purple-400 shrink-0" />
                  ) : (
                    <Database className="w-4 h-4 text-blue-400 shrink-0" />
                  )}
                  <h3 className="font-mono text-xs font-bold text-white truncate">
                    {item.filename}
                  </h3>
                </div>

                <p className="text-xs text-slate-300 font-sans mt-2 line-clamp-2 leading-relaxed">
                  {item.extractedEvent}
                </p>

                <div className="mt-3 pt-2.5 border-t border-slate-800/70 flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>Target: {item.assetId}</span>
                  <span>{item.fileSize}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Detailed Deep Inspector (7 Cols) */}
        <div className="lg:col-span-7 rounded-xl border border-slate-800 bg-[#090e1b] p-6 flex flex-col justify-between shadow-xl space-y-6">
          {activeEvidence ? (
            <div className="space-y-6">
              {/* Top Banner */}
              <div className="flex items-start justify-between pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <EvidenceBadge category={activeEvidence.sourceType} size="sm" />
                    <span className="text-xs font-mono text-slate-500">
                      ID: {activeEvidence.id}
                    </span>
                  </div>
                  <h2 className="text-lg font-mono font-bold text-white flex items-center gap-2">
                    {activeEvidence.filename}
                  </h2>
                </div>
                <div className="text-right font-mono text-xs">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
                    <ShieldCheck className="w-4 h-4" />
                    <span>{activeEvidence.confidence}% Grounded</span>
                  </div>
                  <span className="text-slate-500 text-[11px]">Audit Hash Validated</span>
                </div>
              </div>

              {/* 7 Required Industrial Evidence Details */}
              <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800 font-mono text-xs">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">1. Source System</span>
                  <span className="text-slate-200 font-semibold">{activeEvidence.source}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">2. Source Type</span>
                  <span className="text-cyan-300 font-semibold">{activeEvidence.sourceType}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">3. Original Timestamp</span>
                  <span className="text-slate-300">{activeEvidence.timestamp}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Normalized Timestamp</span>
                  <span className="text-slate-300">{activeEvidence.normalizedTimestamp}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">4. Asset Linked</span>
                  <span className="text-cyan-400 font-bold">
                    {activeEvidence.assetId} ({activeEvidence.assetName})
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">5. Confidence Score</span>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-24 h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-emerald-400 rounded-full"
                        style={{ width: `${activeEvidence.confidence}%` }}
                      />
                    </div>
                    <span className="text-emerald-400 font-bold">{activeEvidence.confidence}%</span>
                  </div>
                </div>
              </div>

              {/* 6. Extracted Event */}
              <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-800/40">
                <span className="text-cyan-400 font-mono text-xs uppercase font-bold tracking-wider flex items-center gap-2 mb-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  6. Extracted Incident Event
                </span>
                <p className="text-sm text-cyan-100 font-sans leading-relaxed">
                  {activeEvidence.extractedEvent}
                </p>
              </div>

              {/* 7. Original Evidence Reference */}
              <div>
                <span className="text-slate-400 font-mono text-xs uppercase font-bold tracking-wider block mb-1.5">
                  7. Original Evidence Reference (Provenance Anchor)
                </span>
                <div className="p-3 rounded-lg bg-black/40 border border-slate-800 font-mono text-xs text-amber-300 select-all">
                  {activeEvidence.originalEvidenceRef}
                </div>
              </div>

              {/* Raw Ingestion Data Sample */}
              {activeEvidence.previewRows && activeEvidence.previewRows.length > 0 && (
                <div>
                  <span className="text-slate-400 font-mono text-xs uppercase font-bold tracking-wider block mb-2">
                    Raw Telemetry Archive Sample
                  </span>
                  <div className="overflow-x-auto rounded-lg border border-slate-800 bg-black/40">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800">
                        <tr>
                          {Object.keys(activeEvidence.previewRows[0]).map((h) => (
                            <th key={h} className="px-3 py-2 font-semibold">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-300">
                        {activeEvidence.previewRows.map((row, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/40">
                            {Object.values(row).map((v, cIdx) => (
                              <td key={cIdx} className="px-3 py-2 whitespace-nowrap">
                                {String(v)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {activeEvidence.rawContent && (
                <div>
                  <span className="text-slate-400 font-mono text-xs uppercase font-bold tracking-wider block mb-2">
                    Ingested Document Excerpt
                  </span>
                  <pre className="p-4 rounded-lg border border-slate-800 bg-black/40 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                    {activeEvidence.rawContent}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center text-slate-500 font-mono text-xs">
              Select an evidence source to view provenance audit logs.
            </div>
          )}

          <div className="pt-4 border-t border-slate-800 text-[11px] font-mono text-slate-500 flex items-center justify-between">
            <span>Evidence Immutability: SHA-256 Validated</span>
            <span>Non-Destructive Normalization</span>
          </div>
        </div>
      </div>
    </div>
  );
};
