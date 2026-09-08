import React from 'react';
import { Evidence } from '../../types';
import { EvidenceBadge } from '../common/EvidenceBadge';
import { X, ShieldCheck, FileSpreadsheet, FileCode, CheckCircle, Database } from 'lucide-react';

interface EvidenceModalProps {
  evidence: Evidence | null;
  onClose: () => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({ evidence, onClose }) => {
  if (!evidence) return null;

  return (
    <div
      id="evidence-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        id="evidence-modal-container"
        className="relative w-full max-w-3xl rounded-xl border border-slate-800 bg-[#0c121e] text-slate-200 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-[#0e1626]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
              {evidence.format === 'csv' ? (
                <FileSpreadsheet className="w-5 h-5" />
              ) : evidence.format === 'pdf' ? (
                <FileCode className="w-5 h-5" />
              ) : (
                <Database className="w-5 h-5" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold font-mono text-white">{evidence.filename}</h3>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                  {evidence.fileSize}
                </span>
              </div>
              <p className="text-xs text-slate-400">ID: {evidence.id} • Source: {evidence.source}</p>
            </div>
          </div>
          <button
            id="close-evidence-modal-btn"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 p-4 rounded-lg bg-slate-900/60 border border-slate-800/80 font-mono text-xs">
            <div>
              <span className="text-slate-500 block mb-1">Source Type</span>
              <EvidenceBadge category={evidence.sourceType} size="sm" />
            </div>
            <div>
              <span className="text-slate-500 block mb-1">Target Asset</span>
              <span className="text-cyan-300 font-semibold px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-900/50">
                {evidence.assetId} ({evidence.assetName})
              </span>
            </div>
            <div>
              <span className="text-slate-500 block mb-1">Normalized Timestamp</span>
              <span className="text-slate-200">{evidence.normalizedTimestamp}</span>
            </div>
            <div>
              <span className="text-slate-500 block mb-1">Original Log Time</span>
              <span className="text-slate-300">{evidence.timestamp}</span>
            </div>
            <div>
              <span className="text-slate-500 block mb-1">Provenance Confidence</span>
              <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{evidence.confidence}% Grounded</span>
              </div>
            </div>
            <div>
              <span className="text-slate-500 block mb-1">Source System</span>
              <span className="text-slate-300 truncate block" title={evidence.source}>
                {evidence.source}
              </span>
            </div>
          </div>

          {/* Extracted Event & Grounding */}
          <div className="p-4 rounded-lg bg-cyan-950/20 border border-cyan-800/40">
            <div className="flex items-center gap-2 mb-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider font-mono">
              <CheckCircle className="w-4 h-4" />
              <span>Extracted Incident Event</span>
            </div>
            <p className="text-sm text-cyan-100/90 leading-relaxed font-sans">
              {evidence.extractedEvent}
            </p>
          </div>

          {/* Original Evidence Reference */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                Original Evidence Reference / Provenance Pointer
              </label>
              <span className="text-[11px] font-mono text-slate-500">Immutable Audit Record</span>
            </div>
            <div className="p-3 rounded-lg bg-black/40 border border-slate-800 font-mono text-xs text-amber-300/90 select-all">
              {evidence.originalEvidenceRef}
            </div>
          </div>

          {/* Raw Artifact / Preview */}
          {evidence.previewRows && evidence.previewRows.length > 0 && (
            <div>
              <label className="text-xs font-mono text-slate-400 uppercase tracking-wider block mb-2">
                Ingested Telemetry Sample (Raw Records)
              </label>
              <div className="overflow-x-auto rounded-lg border border-slate-800 bg-black/30">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800">
                    <tr>
                      {Object.keys(evidence.previewRows[0]).map((key) => (
                        <th key={key} className="px-3 py-2 font-medium">
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {evidence.previewRows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                        {Object.values(row).map((val, cIdx) => (
                          <td key={cIdx} className="px-3 py-2 whitespace-nowrap">
                            {String(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {evidence.rawContent && (
            <div>
              <label className="text-xs font-mono text-slate-400 uppercase tracking-wider block mb-2">
                Document / Observation Excerpt
              </label>
              <pre className="p-4 rounded-lg border border-slate-800 bg-black/40 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                {evidence.rawContent}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-800 px-6 py-3 bg-[#0a0f1a] text-xs font-mono text-slate-500">
          <span>Provenance Verified • SHA-256 Checksum Validated</span>
          <button
            id="close-modal-footer-btn"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition-colors"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
};
