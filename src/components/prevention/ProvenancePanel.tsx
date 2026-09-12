import React from 'react';
import { PreventionEvidenceCitation, Evidence } from '../../types';
import { FileText, ExternalLink, Calendar, Hash, Tag, Layers } from 'lucide-react';

interface ProvenancePanelProps {
  sources: PreventionEvidenceCitation[];
  evidenceList?: Evidence[];
  onSelectEvidenceById?: (evidenceId: string) => void;
}

export const ProvenancePanel: React.FC<ProvenancePanelProps> = ({
  sources,
  evidenceList = [],
  onSelectEvidenceById,
}) => {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <section
      id="prevention-sources-provenance-panel"
      className="rounded-xl border border-slate-800 bg-[#090e1a] overflow-hidden shadow-lg"
    >
      <div className="px-6 py-3.5 bg-[#0d1424] border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-cyan-400" />
          <h3 className="font-mono text-xs font-bold uppercase tracking-wider text-slate-200">
            Source Evidence Provenance
          </h3>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
          {sources.length} Verified Sources Grounded
        </span>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sources.map((src, idx) => {
            const evId = src.evidence_id || src.evidenceId || `EVD-${idx}`;
            const filename = src.filename || 'Unknown File';
            const sourceType = src.source_type || src.sourceType || 'Industrial Evidence';
            const timestamp = src.timestamp;
            const ref = src.original_reference || src.originalReference;
            const assetId = src.asset_id || src.assetId;
            const chunkId = src.chunk_id || src.chunkId;

            return (
              <div
                key={`${evId}-${idx}`}
                id={`provenance-card-${evId.toLowerCase()}`}
                onClick={() => onSelectEvidenceById && onSelectEvidenceById(evId)}
                className="rounded-lg border border-slate-800 bg-[#070b14] p-4 space-y-2.5 hover:border-cyan-800/80 transition-all cursor-pointer group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-cyan-400 px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/60 group-hover:border-cyan-500 transition-colors">
                    {evId}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 truncate max-w-[130px]">
                    {sourceType}
                  </span>
                </div>

                <div>
                  <h4 className="text-xs font-semibold font-mono text-slate-200 truncate group-hover:text-cyan-200 transition-colors">
                    {filename}
                  </h4>
                  {ref && (
                    <p className="text-[11px] font-sans text-slate-400 line-clamp-2 mt-1 leading-snug">
                      {ref}
                    </p>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-800/70 flex items-center justify-between text-[10px] font-mono text-slate-500">
                  {timestamp ? (
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-slate-400" />
                      <span>{new Date(timestamp).toLocaleDateString()}</span>
                    </span>
                  ) : (
                    <span>Timestamp: N/A</span>
                  )}
                  {assetId && (
                    <span className="text-slate-400 font-bold bg-slate-800/80 px-1.5 py-0.5 rounded">
                      {assetId}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
