import React from 'react';
import { PotentialPreventionPath, Evidence } from '../../types';
import { EvidenceBadge } from '../common/EvidenceBadge';
import {
  HelpCircle,
  ClipboardCheck,
  AlertTriangle,
  Lightbulb,
  FileText,
  Tag,
  Cpu,
  Layers,
} from 'lucide-react';

interface PreventionPathCardProps {
  path: PotentialPreventionPath;
  evidenceList?: Evidence[];
  onSelectEvidenceById?: (evidenceId: string) => void;
}

export const PreventionPathCard: React.FC<PreventionPathCardProps> = ({
  path,
  evidenceList = [],
  onSelectEvidenceById,
}) => {
  const pathId = path.path_id || path.pathId || 'PP-???';
  const title = path.title;
  const intervention = path.hypothetical_intervention || path.hypotheticalIntervention || '';
  const potentialEffect = path.potential_effect || path.potentialEffect || '';
  const evidenceBasis = path.evidence_basis || path.evidenceBasis || '';
  const evidenceIds = path.evidence_ids || path.evidenceIds || [];
  const eventIds = path.event_ids || path.eventIds || [];
  const assetIds = path.asset_ids || path.assetIds || [];
  const uncertainties = path.uncertainties || [];
  const verificationChecks = path.verification_checks || path.verificationChecks || [];

  return (
    <article
      id={`prevention-path-card-${pathId.toLowerCase()}`}
      className="rounded-xl border border-slate-800/90 bg-[#090e1a]/95 text-slate-200 shadow-xl overflow-hidden transition-all duration-200 hover:border-slate-700/80"
    >
      {/* Header Banner */}
      <div className="px-6 py-4 border-b border-slate-800/80 bg-[#0d1424] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            id={`badge-path-id-${pathId.toLowerCase()}`}
            className="px-2.5 py-1 rounded bg-amber-950/60 border border-amber-700/70 text-amber-300 font-mono text-xs font-bold tracking-wider"
          >
            {pathId}
          </span>
          <h2
            id={`heading-path-${pathId.toLowerCase()}`}
            className="text-base sm:text-lg font-semibold font-mono text-white tracking-tight"
          >
            {title}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded bg-amber-950/40 border border-amber-800/50 text-amber-400 font-bold uppercase tracking-wider">
            Hypothetical Opportunity
          </span>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Top Distinction: Factual Evidence Basis vs Hypothetical Intervention */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Section A: Factual Evidence Basis (Neutral / Cool) */}
          <div
            id={`section-evidence-basis-${pathId.toLowerCase()}`}
            className="rounded-lg border border-slate-700/60 bg-[#080d17] p-4 flex flex-col justify-between space-y-3"
          >
            <div>
              <div className="flex items-center gap-2 pb-2 mb-2 border-b border-slate-800">
                <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-300">
                  Factual Evidence Basis
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950/80 border border-cyan-800 text-cyan-400 ml-auto">
                  OBSERVED RECORD
                </span>
              </div>
              <p className="text-xs sm:text-sm font-sans text-slate-300 leading-relaxed">
                {evidenceBasis}
              </p>
            </div>
            <div className="pt-2 text-[11px] font-mono text-slate-400 flex items-center gap-1.5 border-t border-slate-800/60">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>Direct operational & engineering records</span>
            </div>
          </div>

          {/* Section B: Hypothetical Intervention (Amber Tone) */}
          <div
            id={`section-hypothetical-intervention-${pathId.toLowerCase()}`}
            className="rounded-lg border border-amber-900/60 bg-gradient-to-br from-amber-950/20 to-[#0c0d18] p-4 flex flex-col justify-between space-y-3"
          >
            <div>
              <div className="flex items-center gap-2 pb-2 mb-2 border-b border-amber-900/40">
                <Lightbulb className="w-4 h-4 text-amber-400 shrink-0" />
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-300">
                  Hypothetical Intervention
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 border border-amber-700 text-amber-300 font-bold ml-auto">
                  HYPOTHETICAL
                </span>
              </div>
              <p className="text-xs sm:text-sm font-sans text-amber-100/90 leading-relaxed font-medium">
                {intervention}
              </p>
            </div>
            <div className="pt-2 text-[11px] font-mono text-amber-300/80 flex items-center gap-1.5 border-t border-amber-900/40">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              <span>Counterfactual window; not a control instruction</span>
            </div>
          </div>
        </div>

        {/* Potential Effect (Clearly Labeled as NOT Guaranteed) */}
        <div
          id={`section-potential-effect-${pathId.toLowerCase()}`}
          className="rounded-lg border border-slate-800 bg-[#0c121e]/80 p-4 space-y-2"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
              Potential Effect — Not Guaranteed
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">
              UNPROVEN CAUSATION
            </span>
          </div>
          <p className="text-xs sm:text-sm font-sans text-slate-300/95 leading-relaxed">
            {potentialEffect}
          </p>
        </div>

        {/* Evidence, Event, and Asset Chips */}
        <div
          id={`chips-${pathId.toLowerCase()}`}
          className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-2"
        >
          <span className="text-[11px] font-mono uppercase text-slate-400 font-semibold mr-1">
            References:
          </span>

          {/* Evidence Chips */}
          {evidenceIds.map((evId) => {
            const evMatch = evidenceList.find((e) => e.id === evId);
            return (
              <button
                key={evId}
                type="button"
                id={`chip-evidence-${pathId.toLowerCase()}-${evId.toLowerCase()}`}
                onClick={() => onSelectEvidenceById && onSelectEvidenceById(evId)}
                title={evMatch ? `Click to inspect: ${evMatch.filename} (${evMatch.sourceType})` : `Inspect evidence ${evId}`}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-cyan-950/50 border border-cyan-800/70 text-cyan-300 hover:bg-cyan-900/60 hover:border-cyan-600 font-mono text-xs transition-colors cursor-pointer"
              >
                <FileText className="w-3 h-3 text-cyan-400" />
                <span>{evId}</span>
                {evMatch && (
                  <span className="text-[10px] text-cyan-400/70 truncate max-w-[120px]">
                    • {evMatch.sourceType}
                  </span>
                )}
              </button>
            );
          })}

          {/* Event Chips */}
          {eventIds.map((evtId) => (
            <span
              key={evtId}
              id={`chip-event-${pathId.toLowerCase()}-${evtId.toLowerCase()}`}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-950/40 border border-blue-800/60 text-blue-300 font-mono text-xs"
            >
              <Layers className="w-3 h-3 text-blue-400" />
              <span>{evtId}</span>
            </span>
          ))}

          {/* Asset Chips */}
          {assetIds.map((astId) => (
            <span
              key={astId}
              id={`chip-asset-${pathId.toLowerCase()}-${astId.toLowerCase()}`}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700 text-slate-300 font-mono text-xs"
            >
              <Cpu className="w-3 h-3 text-slate-400" />
              <span>{astId}</span>
            </span>
          ))}
        </div>

        {/* Uncertainties Section: WHAT WE CANNOT CONFIRM */}
        {uncertainties.length > 0 && (
          <div
            id={`section-uncertainties-${pathId.toLowerCase()}`}
            className="rounded-lg border border-amber-900/40 bg-[#120e10] p-4 space-y-2.5"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-300">
                What We Cannot Confirm
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 font-semibold ml-auto">
                EPISTEMIC BOUNDARY
              </span>
            </div>
            <ul className="space-y-1.5 pl-1">
              {uncertainties.map((unc, idx) => (
                <li
                  key={idx}
                  className="text-xs font-sans text-amber-200/80 flex items-start gap-2"
                >
                  <span className="text-amber-500 font-mono select-none">•</span>
                  <span>{unc}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Verification Checks: NEXT INVESTIGATION STEPS (NOT EQUIPMENT CONTROLS) */}
        {verificationChecks.length > 0 && (
          <div
            id={`section-verification-checks-${pathId.toLowerCase()}`}
            className="rounded-lg border border-slate-800 bg-[#0a101d] p-4 space-y-3"
          >
            <div className="flex items-center gap-2 pb-1 border-b border-slate-800/80">
              <ClipboardCheck className="w-4 h-4 text-cyan-400 shrink-0" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                Next Investigation Steps
              </span>
              <span className="text-[10px] font-mono text-slate-500 ml-auto uppercase tracking-wide">
                Evidence Verification • Advisory Only
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {verificationChecks.map((checkItem, idx) => (
                <div
                  key={idx}
                  className="rounded-md border border-slate-800/80 bg-[#080d17] p-3 space-y-2"
                >
                  <div className="flex items-start gap-2">
                    <span className="w-4 h-4 rounded-full bg-slate-800 border border-slate-700 text-slate-300 text-[10px] font-mono flex items-center justify-center shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <p className="text-xs font-sans text-slate-200 font-medium">
                      {checkItem.check}
                    </p>
                  </div>
                  {checkItem.purpose && (
                    <div className="pl-6 text-[11px] font-mono text-slate-400 border-l border-slate-800 ml-2">
                      <span className="text-cyan-400/90 font-semibold">Purpose: </span>
                      <span className="text-slate-300">{checkItem.purpose}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <p className="text-[10px] font-mono text-slate-500 italic">
              Verification checks represent records and telemetry audit tasks for human investigators, not automated machinery controls.
            </p>
          </div>
        )}
      </div>
    </article>
  );
};
