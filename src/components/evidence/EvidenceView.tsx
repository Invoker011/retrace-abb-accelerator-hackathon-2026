import React, { useState, useEffect } from 'react';
import { Evidence, EvidenceCategory, UploadedEvidenceItem } from '../../types';
import { EvidenceBadge } from '../common/EvidenceBadge';
import { UploadEvidenceModal } from './UploadEvidenceModal';
import { evidenceService } from '../../services/evidenceService';
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
  UploadCloud,
  Trash2,
  Hash,
  HardDrive,
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
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [uploadedItems, setUploadedItems] = useState<UploadedEvidenceItem[]>([]);
  const [activeTabFilter, setActiveTabFilter] = useState<'all' | 'synthetic' | 'uploaded'>('all');

  // Load uploaded items from service
  useEffect(() => {
    async function loadUploads() {
      const uploads = await evidenceService.getUploadedEvidence('INC-2026-001');
      setUploadedItems(uploads);
    }
    loadUploads();
  }, []);

  const handleUploadSuccess = (newItem: UploadedEvidenceItem) => {
    setUploadedItems((prev) => [newItem, ...prev.filter((i) => i.evidenceId !== newItem.evidenceId)]);
  };

  // In public demo mode, evidence deletion is disabled/non-interactive to preserve audit records
  // and prevent mutation of the uploaded incident evidence.

  // Convert uploaded items to Evidence representation for uniform display
  const convertedUploadedItems: Evidence[] = uploadedItems.map((item) => {
    let format: 'csv' | 'pdf' | 'text' | 'image' = 'text';
    const ext = item.originalFilename.split('.').pop()?.toLowerCase();
    if (ext === 'csv') format = 'csv';
    else if (ext === 'pdf') format = 'pdf';
    else if (['jpg', 'jpeg', 'png'].includes(ext || '')) format = 'image';

    return {
      id: item.evidenceId,
      filename: item.originalFilename,
      source: `User Ingestion (${item.storageUri.startsWith('gs://') ? 'GCS' : 'Local Storage'})`,
      sourceType: item.sourceType as EvidenceCategory,
      timestamp: item.uploadedAt,
      normalizedTimestamp: item.uploadedAt,
      assetId: item.assetId || 'UNASSIGNED',
      assetName: item.assetId || 'Unassigned Plant Asset',
      extractedEvent: item.description || `Uploaded industrial evidence file: ${item.originalFilename}`,
      confidence: 100,
      originalEvidenceRef: item.storageUri,
      fileSize: `${(item.fileSize / 1024).toFixed(1)} KB`,
      format,
      previewRows: item.metadata?.preview_rows,
      rawContent: item.metadata?.preview_text,
    };
  });

  // Combine baseline synthetic + newly uploaded items based on activeTabFilter
  let combinedList: Evidence[] = [];
  if (activeTabFilter === 'all') {
    combinedList = [...convertedUploadedItems, ...evidenceList];
  } else if (activeTabFilter === 'synthetic') {
    combinedList = [...evidenceList];
  } else {
    combinedList = [...convertedUploadedItems];
  }

  const activeEvidence = selectedEvidence || combinedList[0];

  // Determine if active evidence is an uploaded artifact
  const activeUploadedRecord = uploadedItems.find(
    (u) => u.evidenceId.toUpperCase() === activeEvidence?.id.toUpperCase()
  );

  const categories: string[] = [
    'ALL',
    'PLC / SCADA',
    'VFD / Drive Logs',
    'Historian Data',
    'Engineering Documents',
    'Maintenance / Inspection Records',
    'Technician Notes & Photos',
  ];

  const filteredEvidence = combinedList.filter((item) => {
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
            {uploadedItems.length > 0 && (
              <span className="text-xs px-2 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300 font-mono">
                {uploadedItems.length} Uploaded
              </span>
            )}
          </div>
          <h1 className="text-2xl font-bold font-mono text-white mt-1">
            Industrial Evidence Repository
          </h1>
          <p className="text-xs text-slate-400 font-sans">
            Immutable provenance logs, telemetry extracts, and engineering records for INC-2026-001.
          </p>
        </div>

        {/* Action Controls: Search + Upload Evidence Button */}
        <div className="flex items-center gap-3">
          <div className="relative w-full md:w-64">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search artifacts, tags, rows..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <button
            id="open-upload-evidence-modal-btn"
            onClick={() => setIsUploadModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold transition-all shadow-lg shadow-cyan-950/60 shrink-0"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Evidence</span>
          </button>
        </div>
      </div>

      {/* Origin Tab Filters & Category Pills */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
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

        {/* Origin Scope Toggle */}
        <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono self-start md:self-auto">
          <button
            onClick={() => setActiveTabFilter('all')}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeTabFilter === 'all'
                ? 'bg-slate-800 text-white font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            All ({evidenceList.length + uploadedItems.length})
          </button>
          <button
            onClick={() => setActiveTabFilter('synthetic')}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeTabFilter === 'synthetic'
                ? 'bg-slate-800 text-cyan-300 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Synthetic Grounding ({evidenceList.length})
          </button>
          <button
            onClick={() => setActiveTabFilter('uploaded')}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeTabFilter === 'uploaded'
                ? 'bg-slate-800 text-blue-300 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Newly Uploaded ({uploadedItems.length})
          </button>
        </div>
      </div>

      {/* Main 2-Column Split: List + Deep Provenance Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Artifact List (5 Cols) */}
        <div className="lg:col-span-5 space-y-3 max-h-[75vh] overflow-y-auto pr-1">
          {filteredEvidence.length === 0 ? (
            <div className="p-8 rounded-xl border border-slate-800 bg-[#0a0f1d] text-center text-slate-500 font-mono text-xs">
              No evidence artifacts match the selected filters.
            </div>
          ) : (
            filteredEvidence.map((item) => {
              const isSelected = activeEvidence?.id === item.id;
              const isUploaded = uploadedItems.some((u) => u.evidenceId === item.id);

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
                    <div className="flex items-center gap-1.5">
                      <EvidenceBadge category={item.sourceType} size="sm" />
                      {isUploaded && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-mono font-bold">
                          NEWLY UPLOADED
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                      {isUploaded ? 'UPLOADED' : `${item.confidence}% Grounded`}
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
            })
          )}
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
                    {activeUploadedRecord && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-mono font-bold">
                        STATUS: {activeUploadedRecord.processingStatus}
                      </span>
                    )}
                  </div>
                  <h2 className="text-lg font-mono font-bold text-white flex items-center gap-2">
                    {activeEvidence.filename}
                  </h2>
                </div>

                <div className="flex items-center gap-3">
                  {activeUploadedRecord && (
                    <button
                      id="delete-uploaded-evidence-btn"
                      disabled={true}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-950/20 border border-rose-900/40 text-rose-400/50 font-mono text-xs cursor-not-allowed opacity-60"
                      title="Disabled in public demo"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Delete</span>
                    </button>
                  )}

                  <div className="text-right font-mono text-xs">
                    <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
                      <ShieldCheck className="w-4 h-4" />
                      <span>{activeUploadedRecord ? 'Verified SHA-256' : `${activeEvidence.confidence}% Grounded`}</span>
                    </div>
                    <span className="text-slate-500 text-[11px]">Audit Hash Validated</span>
                  </div>
                </div>
              </div>

              {/* 7 Industrial Evidence Provenance Details */}
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
                  <span className="text-slate-500 block text-[10px] uppercase">5. Processing Status</span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-emerald-800/60 font-bold">
                      {activeUploadedRecord ? activeUploadedRecord.processingStatus : 'GROUNDED'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Extracted Event / Description */}
              <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-800/40">
                <span className="text-cyan-400 font-mono text-xs uppercase font-bold tracking-wider flex items-center gap-2 mb-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  6. Extracted Incident Event / Summary
                </span>
                <p className="text-sm text-cyan-100 font-sans leading-relaxed">
                  {activeEvidence.extractedEvent}
                </p>
              </div>

              {/* Original Evidence Reference / Storage URI */}
              <div>
                <span className="text-slate-400 font-mono text-xs uppercase font-bold tracking-wider block mb-1.5">
                  7. Original Evidence Reference & Storage URI
                </span>
                <div className="p-3 rounded-lg bg-black/40 border border-slate-800 font-mono text-xs text-amber-300 select-all break-all">
                  {activeEvidence.originalEvidenceRef}
                </div>
              </div>

              {/* SHA-256 Digest for Uploaded Item */}
              {activeUploadedRecord && (
                <div className="p-3 rounded-lg bg-black/40 border border-emerald-900/60 font-mono text-xs">
                  <span className="text-emerald-400 uppercase text-[10px] font-bold block mb-1">
                    SHA-256 Audit Integrity Digest
                  </span>
                  <div className="text-emerald-300 text-[11px] select-all break-all flex items-center gap-2">
                    <Hash className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{activeUploadedRecord.sha256Hash}</span>
                  </div>
                </div>
              )}

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
                    Ingested Document Excerpt / Content Preview
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

      {/* Upload Evidence Modal */}
      <UploadEvidenceModal
        incidentId="INC-2026-001"
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
};

