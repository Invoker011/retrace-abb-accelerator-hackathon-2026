import React, { useState, useEffect } from 'react';
import {
  PotentialPreventionPath,
  PreventionPathsResponse,
  Evidence,
  Incident,
} from '../../types';
import { preventionService } from '../../services/preventionService';
import { PreventionPathCard } from './PreventionPathCard';
import { ProvenancePanel } from './ProvenancePanel';
import {
  ShieldAlert,
  AlertTriangle,
  FileText,
  Search,
  RefreshCw,
  HelpCircle,
  ArrowRight,
  Sparkles,
  Info,
  CheckCircle,
  Database,
  Layers,
  PlaySquare,
  MessageSquareCode,
} from 'lucide-react';

interface PreventionViewProps {
  incidentId?: string;
  incident?: Incident;
  evidenceList?: Evidence[];
  onSelectEvidenceById?: (evidenceId: string) => void;
  onNavigateToView?: (view: 'replay' | 'investigation' | 'incidents' | 'evidence') => void;
}

const DEFAULT_QUERY = 'What could potentially have prevented or mitigated this incident?';

const LOADING_STEPS = [
  'Retrieving incident evidence & temporal context...',
  'Reviewing maintenance and engineering records...',
  'Evaluating hypothetical counterfactual opportunities...',
  'Validating citations, uncertainty bounds, and grounding...',
];

export const PreventionView: React.FC<PreventionViewProps> = ({
  incidentId = 'INC-2026-001',
  incident,
  evidenceList = [],
  onSelectEvidenceById,
  onNavigateToView,
}) => {
  const [data, setData] = useState<PreventionPathsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingStepIdx, setLoadingStepIdx] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [queryInput, setQueryInput] = useState<string>(DEFAULT_QUERY);
  const [activeQuery, setActiveQuery] = useState<string>(DEFAULT_QUERY);

  // Cycle loading step messages during processing
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (loading) {
      setLoadingStepIdx(0);
      interval = setInterval(() => {
        setLoadingStepIdx((prev) => (prev + 1) % LOADING_STEPS.length);
      }, 3500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loading]);

  // Fetch prevention paths from backend API
  const fetchPreventionPaths = async (queryToRun: string) => {
    setLoading(true);
    setError(null);

    try {
      const res = await preventionService.getPreventionPaths(incidentId, {
        query: queryToRun,
      });

      if (!res) {
        throw new Error('No response returned from prevention service');
      }

      setData(res);
      setActiveQuery(queryToRun);
    } catch (err: unknown) {
      console.error('[RETRACE] Prevention paths fetch error:', err);
      setError('Unable to produce a validated prevention analysis.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPreventionPaths(DEFAULT_QUERY);
  }, [incidentId]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanQuery = queryInput.trim();
    if (!cleanQuery) return;
    fetchPreventionPaths(cleanQuery);
  };

  const handleResetQuery = () => {
    setQueryInput(DEFAULT_QUERY);
    fetchPreventionPaths(DEFAULT_QUERY);
  };

  const paths: PotentialPreventionPath[] = data?.paths || [];
  const sources = data?.sources_used || data?.sourcesUsed || [];
  const unknowns = data?.unknowns || [];
  const summary = data?.summary || '';
  const disclaimer = data?.disclaimer || '';

  return (
    <div id="prevention-view" className="p-6 sm:p-8 max-w-7xl mx-auto space-y-8">
      {/* 1. Header & Investigation Stage Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span
              id="badge-counterfactual-analysis"
              className="text-xs px-2.5 py-0.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 font-mono font-bold uppercase tracking-wider"
            >
              Counterfactual Analysis
            </span>
            <span
              id="badge-advisory-only"
              className="text-xs px-2.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono font-bold uppercase tracking-wider"
            >
              Advisory Only
            </span>
            <span className="text-xs font-mono text-slate-500">
              Incident: <span className="text-slate-300 font-semibold">{incidentId}</span>
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold font-mono text-white mt-2">
            What Could Have Prevented It?
          </h1>
          <p className="text-sm text-slate-400 font-sans mt-0.5">
            Potential Prevention Paths • Evidence-grounded exploratory intervention opportunities.
          </p>
        </div>

        {/* Navigation Breadcrumb to Replay & Grounded Chat */}
        {onNavigateToView && (
          <div className="flex items-center gap-2 text-xs font-mono">
            <button
              onClick={() => onNavigateToView('replay')}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center gap-1.5 transition-colors"
            >
              <PlaySquare className="w-3.5 h-3.5 text-cyan-400" />
              <span>Incident Replay</span>
            </button>
            <button
              onClick={() => onNavigateToView('investigation')}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center gap-1.5 transition-colors"
            >
              <MessageSquareCode className="w-3.5 h-3.5 text-blue-400" />
              <span>Grounded Chat</span>
            </button>
          </div>
        )}
      </div>

      {/* 2. Top Governance Banner (Required Epistemic Clarification) */}
      <div
        id="prevention-governance-banner"
        className="p-4 sm:p-5 rounded-xl bg-amber-950/25 border border-amber-700/60 flex items-start gap-3.5 text-amber-200 shadow-md"
      >
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase font-bold text-amber-300 tracking-wider">
              Epistemic Notice & Governance
            </span>
            <span className="text-[10px] font-mono px-2 py-0.2 rounded bg-amber-950 border border-amber-800 text-amber-400 font-semibold">
              DECISION SUPPORT
            </span>
          </div>
          <p className="text-xs sm:text-sm font-sans leading-relaxed text-amber-100 font-medium">
            "These are evidence-grounded hypothetical opportunities. They do not prove causation or guarantee prevention."
          </p>
          <p className="text-[11px] font-mono text-amber-300/80">
            RETRACE does not execute machine controls, override safety interlocks, or alter PLC/VFD parameters. All scenarios require human engineering review.
          </p>
        </div>
      </div>

      {/* 3. Query Bar: Optional Investigator Question */}
      <div
        id="prevention-query-section"
        className="rounded-xl border border-slate-800 bg-[#0c121e] p-4 sm:p-5 shadow-lg space-y-3"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-cyan-400" />
            <label
              htmlFor="prevention-query-input"
              className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200"
            >
              Focus Prevention Question
            </label>
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Sends query to evidence-grounded counterfactual reasoning
          </span>
        </div>

        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <input
              id="prevention-query-input"
              type="text"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="e.g. What earlier warning signals could have been acted on?"
              disabled={loading}
              className="w-full bg-[#070b14] border border-slate-700/80 rounded-lg px-4 py-2.5 text-xs sm:text-sm font-sans text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition-colors disabled:opacity-50"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
            <button
              id="analyze-prevention-paths-btn"
              type="submit"
              disabled={loading || !queryInput.trim()}
              className="w-full sm:w-auto px-4 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 active:bg-cyan-700 text-black font-mono text-xs font-bold transition-all shadow-md hover:shadow-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Analyze Potential Paths</span>
                </>
              )}
            </button>

            {queryInput !== DEFAULT_QUERY && (
              <button
                type="button"
                onClick={handleResetQuery}
                disabled={loading}
                className="px-3 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs transition-colors cursor-pointer"
                title="Reset to default question"
              >
                Reset
              </button>
            )}
          </div>
        </form>

        {/* Quick Suggestion Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] font-mono text-slate-500">Quick queries:</span>
          <button
            type="button"
            disabled={loading}
            onClick={() => {
              setQueryInput('What earlier warning signals could have been acted on?');
              fetchPreventionPaths('What earlier warning signals could have been acted on?');
            }}
            className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-cyan-300 hover:border-cyan-800 transition-colors cursor-pointer"
          >
            Earlier warning signals
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => {
              setQueryInput('Could maintenance follow-up have provided an earlier inspection opportunity?');
              fetchPreventionPaths('Could maintenance follow-up have provided an earlier inspection opportunity?');
            }}
            className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-cyan-300 hover:border-cyan-800 transition-colors cursor-pointer"
          >
            Maintenance follow-up opportunity
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => {
              setQueryInput('What could earlier review of suction pressure have mitigated?');
              fetchPreventionPaths('What could earlier review of suction pressure have mitigated?');
            }}
            className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-cyan-300 hover:border-cyan-800 transition-colors cursor-pointer"
          >
            Suction pressure condition
          </button>
        </div>
      </div>

      {/* 4. Loading State */}
      {loading && (
        <div
          id="prevention-loading-container"
          className="rounded-xl border border-slate-800 bg-[#0a0f1d] p-12 text-center space-y-6 shadow-xl animate-in fade-in"
        >
          <div className="flex justify-center">
            <div className="relative">
              <div className="w-14 h-14 rounded-full border-2 border-cyan-500/20 border-t-cyan-400 animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" />
              </div>
            </div>
          </div>
          <div className="space-y-2">
            <h3 className="text-base font-mono font-bold text-white">
              Generating Grounded Prevention Analysis
            </h3>
            <p className="text-xs font-mono text-cyan-400 transition-all duration-300">
              {LOADING_STEPS[loadingStepIdx]}
            </p>
            <p className="text-xs font-sans text-slate-400 max-w-md mx-auto pt-2">
              Cross-referencing telemetry time-series, CMMS work orders, VFD fault logs, and engineering manuals with strict epistemic validation.
            </p>
          </div>
        </div>
      )}

      {/* 5. Error State */}
      {!loading && error && (
        <div
          id="prevention-error-container"
          className="rounded-xl border border-rose-900/60 bg-rose-950/20 p-8 text-center space-y-4 shadow-xl"
        >
          <div className="w-12 h-12 rounded-full bg-rose-950 border border-rose-800 text-rose-400 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-mono font-bold text-rose-300">
              {error}
            </h3>
            <p className="text-xs font-sans text-slate-300 max-w-lg mx-auto">
              The counterfactual reasoning service could not establish a fully grounded set of prevention paths for this query.
            </p>
          </div>
          <div className="pt-2">
            <button
              id="retry-prevention-paths-btn"
              onClick={() => fetchPreventionPaths(activeQuery)}
              className="px-4 py-2 rounded-lg bg-rose-900 hover:bg-rose-800 text-white font-mono text-xs font-bold transition-colors inline-flex items-center gap-2 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Analysis</span>
            </button>
          </div>
        </div>
      )}

      {/* 6. Success State */}
      {!loading && !error && data && (
        <div className="space-y-8">
          {/* Top Summary Block */}
          <div
            id="prevention-summary-container"
            className="rounded-xl border border-slate-800 bg-[#090e1a] p-6 space-y-4 shadow-xl"
          >
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                  Incident Synthesis & Grounded Context
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  {data.incident_id || incidentId}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono">
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-950/40 border border-amber-800/40 text-amber-300">
                  <span className="font-bold">{paths.length}</span>
                  <span className="text-slate-400">Paths Identified</span>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-cyan-950/40 border border-cyan-800/40 text-cyan-300">
                  <span className="font-bold">{sources.length}</span>
                  <span className="text-slate-400">Sources Used</span>
                </div>
              </div>
            </div>

            {summary && (
              <div className="space-y-1.5">
                <p className="text-xs sm:text-sm font-sans text-slate-300 leading-relaxed">
                  {summary}
                </p>
              </div>
            )}

            {/* Global Unknowns (if any returned by backend) */}
            {unknowns.length > 0 && (
              <div
                id="prevention-global-unknowns"
                className="pt-3 border-t border-slate-800/80 space-y-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold uppercase text-slate-400">
                    Documented Evidence Unknowns:
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                    UNCONFIRMED CORRELATIONS
                  </span>
                </div>
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {unknowns.map((unk, idx) => (
                    <li
                      key={idx}
                      className="text-xs font-sans text-slate-400 flex items-start gap-2 bg-[#070b14] p-2.5 rounded border border-slate-800/60"
                    >
                      <span className="text-amber-400 font-mono text-sm leading-none">•</span>
                      <span>{unk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* 7. Prevention Path Cards */}
          <div id="prevention-paths-list" className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200">
                  Evaluated Potential Prevention Paths
                </h2>
                <span className="text-xs font-mono text-slate-500">
                  ({paths.length} scenarios)
                </span>
              </div>
              <span className="text-[11px] font-mono text-amber-400/90">
                Sorted by operational precedence
              </span>
            </div>

            {paths.length === 0 ? (
              /* Empty State (Valid result per instructions) */
              <div
                id="prevention-empty-state"
                className="rounded-xl border border-slate-800 bg-[#090e1a] p-12 text-center space-y-3"
              >
                <Info className="w-8 h-8 text-slate-500 mx-auto" />
                <h3 className="text-base font-mono font-bold text-slate-200">
                  No Sufficiently Grounded Paths
                </h3>
                <p className="text-xs font-sans text-slate-400 max-w-lg mx-auto">
                  "No sufficiently grounded prevention paths could be established from the available evidence."
                </p>
                <div className="pt-2">
                  <button
                    onClick={handleResetQuery}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300 transition-colors"
                  >
                    Reset Query
                  </button>
                </div>
              </div>
            ) : (
              paths.map((path) => (
                <PreventionPathCard
                  key={path.path_id || path.pathId || path.title}
                  path={path}
                  evidenceList={evidenceList}
                  onSelectEvidenceById={onSelectEvidenceById}
                />
              ))
            )}
          </div>

          {/* 8. Source Provenance Panel */}
          <ProvenancePanel
            sources={sources}
            evidenceList={evidenceList}
            onSelectEvidenceById={onSelectEvidenceById}
          />

          {/* 9. Top-Level Official API Disclaimer */}
          {disclaimer && (
            <div
              id="prevention-api-disclaimer"
              className="p-5 rounded-xl border border-slate-800 bg-[#080d17] flex items-start gap-3.5 text-slate-400 font-mono text-xs leading-relaxed"
            >
              <Info className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-bold text-slate-300 uppercase tracking-wider text-[11px]">
                  RETRACE Epistemic & Advisory Disclaimer
                </span>
                <p className="font-sans text-slate-400 leading-relaxed text-xs">
                  "{disclaimer}"
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
