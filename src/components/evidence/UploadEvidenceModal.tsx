import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  X,
  FileSpreadsheet,
  FileText,
  FileCode,
  Image as ImageIcon,
  CheckCircle2,
  AlertCircle,
  Hash,
  ShieldCheck,
  Cpu,
} from 'lucide-react';
import { EvidenceCategory, UploadedEvidenceItem } from '../../types';
import { evidenceService } from '../../services/evidenceService';

interface UploadEvidenceModalProps {
  incidentId: string;
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (item: UploadedEvidenceItem) => void;
}

const EVIDENCE_CATEGORIES: EvidenceCategory[] = [
  'PLC / SCADA',
  'VFD / Drive Logs',
  'Historian Data',
  'Engineering Documents',
  'Maintenance / Inspection Records',
  'Technician Notes & Photos',
];

const KNOWN_ASSETS = [
  { id: 'VFD-204', name: 'Variable Frequency Drive VFD-204' },
  { id: 'M-204', name: 'Induction Motor M-204' },
  { id: 'P-204', name: 'High-Pressure Centrifugal Pump P-204' },
  { id: 'PLC-204', name: 'Control PLC Rack 204' },
];

const ACCEPTED_EXTENSIONS = ['.csv', '.pdf', '.txt', '.jpg', '.jpeg', '.png'];
const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

export const UploadEvidenceModal: React.FC<UploadEvidenceModalProps> = ({
  incidentId,
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [sourceType, setSourceType] = useState<EvidenceCategory>('VFD / Drive Logs');
  const [assetId, setAssetId] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successItem, setSuccessItem] = useState<UploadedEvidenceItem | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const validateAndSetFile = (file: File) => {
    setErrorMessage(null);
    setSuccessItem(null);

    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setErrorMessage(
        `Unsupported file type '${ext}'. Accepted formats are: CSV, PDF, TXT, JPG, PNG.`
      );
      return false;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setErrorMessage(
        `File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the 20 MB limit.`
      );
      return false;
    }

    // Check for nested executable extensions
    const segments = file.name.toLowerCase().split('.');
    const banned = ['exe', 'bat', 'cmd', 'sh', 'bin', 'py', 'js', 'vbs', 'msi'];
    for (const seg of segments.slice(0, -1)) {
      if (banned.includes(seg)) {
        setErrorMessage(`Dangerous nested extension segment '${seg}' is prohibited.`);
        return false;
      }
    }

    setSelectedFile(file);
    return true;
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage('Please select or drop an evidence file to upload.');
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);

    try {
      const result = await evidenceService.uploadEvidence(
        incidentId,
        selectedFile,
        sourceType,
        assetId || undefined,
        description || undefined
      );

      setSuccessItem(result);
      onUploadSuccess(result);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to upload evidence. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleResetForm = () => {
    setSelectedFile(null);
    setDescription('');
    setSuccessItem(null);
    setErrorMessage(null);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes >= 1024 * 1024) {
      return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    }
    return (bytes / 1024).toFixed(1) + ' KB';
  };

  return (
    <div
      id="upload-evidence-modal-overlay"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
    >
      <div
        id="upload-evidence-modal-card"
        className="relative w-full max-w-2xl bg-[#090e1b] border border-slate-700/80 rounded-2xl shadow-2xl p-6 space-y-5 text-white max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-950/80 border border-cyan-700/60 text-cyan-400">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold font-mono text-white">
                Upload Industrial Evidence
              </h2>
              <p className="text-xs text-slate-400 font-sans">
                Register immutable operational, engineering, or maintenance evidence with {incidentId}.
              </p>
            </div>
          </div>
          <button
            id="close-upload-modal-btn"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Success Banner if just uploaded */}
        {successItem ? (
          <div className="space-y-4 p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/60 font-mono text-xs">
            <div className="flex items-center gap-2 text-emerald-400 font-bold">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <span>Evidence Securely Ingested & Registered</span>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-emerald-800/40 text-[11px]">
              <div>
                <span className="text-slate-400 block uppercase text-[10px]">Evidence ID</span>
                <span className="text-white font-bold">{successItem.evidenceId}</span>
              </div>
              <div>
                <span className="text-slate-400 block uppercase text-[10px]">Filename</span>
                <span className="text-cyan-300 truncate block">{successItem.originalFilename}</span>
              </div>
              <div>
                <span className="text-slate-400 block uppercase text-[10px]">Source Category</span>
                <span className="text-slate-200">{successItem.sourceType}</span>
              </div>
              <div>
                <span className="text-slate-400 block uppercase text-[10px]">File Size</span>
                <span className="text-slate-200">{formatFileSize(successItem.fileSize)}</span>
              </div>
              <div>
                <span className="text-slate-400 block uppercase text-[10px]">Related Asset</span>
                <span className="text-cyan-400">{successItem.assetId || 'Unassigned'}</span>
              </div>
              <div>
                <span className="text-slate-400 block uppercase text-[10px]">Processing Status</span>
                <span className="px-2 py-0.5 rounded bg-blue-900/80 border border-blue-700 text-blue-300 font-bold inline-block">
                  {successItem.processingStatus}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-emerald-800/40">
              <span className="text-slate-400 block uppercase text-[10px] mb-1">
                Audit Integrity (SHA-256 Digest)
              </span>
              <div className="p-2 rounded bg-black/60 border border-emerald-900 text-emerald-300 font-mono text-[10px] break-all select-all flex items-center gap-2">
                <Hash className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                <span>{successItem.sha256Hash}</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                id="upload-another-btn"
                onClick={handleResetForm}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs transition-colors"
              >
                Upload Another Artifact
              </button>
              <button
                id="view-evidence-btn"
                onClick={onClose}
                className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold transition-colors"
              >
                Done / View in Repository
              </button>
            </div>
          </div>
        ) : (
          /* Upload Form */
          <form onSubmit={handleSubmit} className="space-y-4 font-mono text-xs">
            {errorMessage && (
              <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span className="font-sans text-xs">{errorMessage}</span>
              </div>
            )}

            {/* Evidence Type */}
            <div className="space-y-1.5">
              <label className="block text-slate-400 text-[11px] uppercase tracking-wider">
                1. Evidence Type <span className="text-rose-400">*</span>
              </label>
              <select
                id="evidence-source-type-select"
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value as EvidenceCategory)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-cyan-500 font-mono text-xs"
              >
                {EVIDENCE_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            {/* File Drag & Drop + Click Box */}
            <div className="space-y-1.5">
              <label className="block text-slate-400 text-[11px] uppercase tracking-wider">
                2. Select File <span className="text-rose-400">*</span>
              </label>

              <div
                id="dropzone-box"
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                  isDragging
                    ? 'border-cyan-400 bg-cyan-950/30'
                    : selectedFile
                    ? 'border-emerald-600/80 bg-emerald-950/20'
                    : 'border-slate-700 hover:border-slate-500 bg-slate-900/40'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.pdf,.txt,.jpg,.jpeg,.png"
                  onChange={handleFileChange}
                  className="hidden"
                  id="evidence-file-input"
                />

                {selectedFile ? (
                  <div className="flex flex-col items-center gap-2">
                    <div className="p-3 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                    <span className="font-bold text-white text-sm">{selectedFile.name}</span>
                    <span className="text-slate-400 text-xs">
                      {formatFileSize(selectedFile.size)} • Click or drop another to replace
                    </span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <div className="p-3 rounded-full bg-slate-800/80 text-cyan-400">
                      <UploadCloud className="w-6 h-6" />
                    </div>
                    <span className="font-semibold text-slate-200">
                      Drag & drop your evidence file here, or{' '}
                      <span className="text-cyan-400 underline">browse</span>
                    </span>
                    <span className="text-[11px] text-slate-500">
                      Supported formats: CSV, PDF, TXT, JPG, PNG (Max 20 MB)
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Related Asset (Optional) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-slate-400 text-[11px] uppercase tracking-wider">
                  3. Related Asset (Optional)
                </label>
                <select
                  id="evidence-asset-id-select"
                  value={assetId}
                  onChange={(e) => setAssetId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-cyan-500 font-mono text-xs"
                >
                  <option value="">-- No specific asset assigned --</option>
                  {KNOWN_ASSETS.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.id} ({asset.name})
                    </option>
                  ))}
                </select>
              </div>

              {/* Security Banner */}
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 flex items-center gap-2.5">
                <ShieldCheck className="w-5 h-5 text-cyan-400 shrink-0" />
                <span className="font-sans">
                  Uploaded files are stored immutably with SHA-256 hashing. Uploaded documents are treated strictly as untrusted data.
                </span>
              </div>
            </div>

            {/* Description (Optional) */}
            <div className="space-y-1.5">
              <label className="block text-slate-400 text-[11px] uppercase tracking-wider">
                4. Description / Observational Context (Optional)
              </label>
              <textarea
                id="evidence-description-textarea"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g., Raw CSV telemetry from drive VFD-204 captured during the 10:14 overcurrent trip."
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-sans text-xs"
              />
            </div>

            {/* Submit / Action Buttons */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                id="cancel-upload-btn"
                onClick={onClose}
                disabled={isUploading}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                id="submit-upload-btn"
                disabled={isUploading || !selectedFile}
                className={`px-5 py-2 rounded-lg font-mono text-xs font-bold flex items-center gap-2 transition-all ${
                  isUploading || !selectedFile
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                    : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-950'
                }`}
              >
                {isUploading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                    <span>Ingesting & Hashing...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-4 h-4" />
                    <span>Upload & Register Evidence</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
