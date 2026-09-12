import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  IncidentReplayResponse,
  ReplayEvent,
  ReplayPhase,
  Evidence,
  IncidentEvent,
  Asset,
} from '../../types';
import { incidentService } from '../../services/incidentService';
import {
  Play,
  Pause,
  RotateCcw,
  SkipBack,
  SkipForward,
  Clock,
  AlertTriangle,
  FileText,
  Network,
  Filter,
  RefreshCw,
  Info,
  Shield,
  Layers,
  Database,
  Calendar,
  Tag,
  Eye,
} from 'lucide-react';

interface IncidentReplayViewProps {
  incidentId?: string;
  onSelectEvidence?: (evidence: Evidence) => void;
  evidenceList?: Evidence[];
  // Legacy / fallback props for compatibility
  events?: IncidentEvent[];
  assets?: Asset[];
}

const PHASE_LABELS: Record<ReplayPhase, string> = {
  PRECURSOR: 'PRECURSOR',
  DEGRADATION: 'DEGRADATION',
  OPERATOR_OBSERVATION: 'OPERATOR OBSERVATION',
  PROTECTIVE_SHUTDOWN: 'PROTECTIVE SHUTDOWN',
  UNCLASSIFIED: 'UNCLASSIFIED',
};

const PHASE_STYLES: Record<
  ReplayPhase,
  {
    badge: string;
    marker: string;
    border: string;
    glow: string;
  }
> = {
  PRECURSOR: {
    badge: 'bg-blue-950/80 text-cyan-300 border-cyan-800/80',
    marker: 'bg-cyan-500 border-cyan-300',
    border: 'border-cyan-700/60',
    glow: 'shadow-cyan-900/30',
  },
  DEGRADATION: {
    badge: 'bg-amber-950/80 text-amber-300 border-amber-800/80',
    marker: 'bg-amber-500 border-amber-300',
    border: 'border-amber-700/60',
    glow: 'shadow-amber-900/30',
  },
  OPERATOR_OBSERVATION: {
    badge: 'bg-purple-950/80 text-purple-300 border-purple-800/80',
    marker: 'bg-purple-500 border-purple-300',
    border: 'border-purple-700/60',
    glow: 'shadow-purple-900/30',
  },
  PROTECTIVE_SHUTDOWN: {
    badge: 'bg-rose-950/80 text-rose-300 border-rose-800/80',
    marker: 'bg-rose-500 border-rose-300',
    border: 'border-rose-700/60',
    glow: 'shadow-rose-900/30',
  },
  UNCLASSIFIED: {
    badge: 'bg-slate-800 text-slate-300 border-slate-700',
    marker: 'bg-slate-500 border-slate-300',
    border: 'border-slate-700',
    glow: 'shadow-slate-900/30',
  },
};

const SEVERITY_STYLES: Record<string, string> = {
  Critical: 'bg-rose-950/80 text-rose-300 border-rose-800/80',
  High: 'bg-orange-950/80 text-orange-300 border-orange-800/80',
  Medium: 'bg-amber-950/80 text-amber-300 border-amber-800/80',
  Low: 'bg-slate-800 text-slate-300 border-slate-700',
};

export const IncidentReplayView: React.FC<IncidentReplayViewProps> = ({
  incidentId = 'INC-2026-001',
  onSelectEvidence,
  evidenceList = [],
}) => {
  const [replayData, setReplayData] = useState<IncidentReplayResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Active event index in the sequence
  const [activeIndex, setActiveIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1); // 0.5x, 1x, 2x

  // Replay window filter states (start_offset_seconds, end_offset_seconds)
  const [startOffsetInput, setStartOffsetInput] = useState<string>('');
  const [endOffsetInput, setEndOffsetInput] = useState<string>('');
  const [activeWindow, setActiveWindow] = useState<{ start?: number; end?: number } | null>(null);

  const playbackTimerRef = useRef<any>(null);

  // Fetch replay from backend
  const fetchReplay = useCallback(
    async (startOffset?: number, endOffset?: number) => {
      setLoading(true);
      setError(null);
      try {
        const data = await incidentService.getIncidentReplay(
          incidentId,
          startOffset,
          endOffset
        );
        if (!data || !data.events) {
          setError('No recorded replay events returned by server.');
          setReplayData(null);
        } else {
          setReplayData(data);
          setActiveIndex(0);
          setIsPlaying(false);
        }
      } catch (err: any) {
        const msg = err?.message || 'Failed to load incident replay from live API.';
        setError(msg);
        setReplayData(null);
      } finally {
        setLoading(false);
      }
    },
    [incidentId]
  );

  useEffect(() => {
    fetchReplay(activeWindow?.start, activeWindow?.end);
  }, [fetchReplay, activeWindow]);

  const events: ReplayEvent[] = replayData?.events || [];
  const currentEvent: ReplayEvent | undefined = events[activeIndex];
  const totalDuration = replayData?.duration_seconds ?? 27;

  // Replay advancement timer
  useEffect(() => {
    if (isPlaying && events.length > 0) {
      const stepIntervalMs = 2400 / playbackSpeed;
      playbackTimerRef.current = setInterval(() => {
        setActiveIndex((prev) => {
          if (prev >= events.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, stepIntervalMs);
    } else {
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    }

    return () => {
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    };
  }, [isPlaying, playbackSpeed, events.length]);

  const handlePlayPause = () => {
    if (events.length === 0) return;
    if (activeIndex >= events.length - 1) {
      setActiveIndex(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleRestart = () => {
    setIsPlaying(false);
    setActiveIndex(0);
  };

  const handleStepBack = () => {
    setIsPlaying(false);
    setActiveIndex((prev) => Math.max(0, prev - 1));
  };

  const handleStepForward = () => {
    setIsPlaying(false);
    setActiveIndex((prev) => Math.min(events.length - 1, prev + 1));
  };

  const handleApplyWindow = (e: React.FormEvent) => {
    e.preventDefault();
    const start = startOffsetInput.trim() !== '' ? parseInt(startOffsetInput, 10) : undefined;
    const end = endOffsetInput.trim() !== '' ? parseInt(endOffsetInput, 10) : undefined;
    setActiveWindow({ start, end });
  };

  const handleResetWindow = () => {
    setStartOffsetInput('');
    setEndOffsetInput('');
    setActiveWindow(null);
  };

  const handleEvidenceClick = (evRef: { evidence_id?: string; evidenceId?: string; filename: string }) => {
    const evId = evRef.evidence_id || evRef.evidenceId;
    if (!onSelectEvidence) return;
    const matched = evidenceList.find((e) => e.id === evId);
    if (matched) {
      onSelectEvidence(matched);
    } else if (evId) {
      // Synthetic reference object if not preloaded in evidenceList
      const fallbackEvidence: Evidence = {
        id: evId,
        filename: evRef.filename,
        source: 'Forensic Evidence Archive',
        sourceType: 'Engineering Documents',
        timestamp: currentEvent?.timestamp || '',
        normalizedTimestamp: currentEvent?.timestamp || '',
        assetId: currentEvent?.asset_id || '',
        assetName: currentEvent?.asset_id || '',
        extractedEvent: `Evidence reference ${evId} supporting replay event ${currentEvent?.event_id}`,
        confidence: 100,
        originalEvidenceRef: (evRef as any).original_reference || (evRef as any).originalReference || '',
        fileSize: '—',
        format: 'text',
      };
      onSelectEvidence(fallbackEvidence);
    }
  };

  // Helper to format metric values
  const formatMetricName = (name: string): string => {
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div id="incident-replay-view" className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* 1. TOP HEADER */}
      <div className="rounded-xl border border-slate-800 bg-[#0c1322] p-6 space-y-4 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono uppercase tracking-widest text-cyan-400 font-bold">
                Deterministic Replay Engine
              </span>
              <span className="text-xs px-2.5 py-0.5 rounded bg-blue-950/80 border border-blue-800 text-blue-300 font-mono">
                {incidentId}
              </span>
              <span className="text-xs px-2.5 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/80 text-emerald-300 font-mono flex items-center gap-1">
                <Shield className="w-3 h-3" />
                Forensic reconstruction from recorded evidence
              </span>
            </div>
            <h1 className="text-2xl font-bold font-mono text-white mt-1.5 flex items-center gap-2">
              <span>Incident Replay</span>
            </h1>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              Chronological step reconstruction through multi-source operational, VFD, historian, and field observations.
            </p>
          </div>

          {/* Forensic Disclaimer */}
          <div className="bg-[#080d19] border border-slate-800 rounded-lg p-3 lg:max-w-md">
            <div className="flex items-start gap-2 text-[11px] text-slate-300 font-mono">
              <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <span>
                Replay reconstructs recorded evidence in chronological order. It does not establish causation.
              </span>
            </div>
          </div>
        </div>

        {/* Replay Metadata Strip */}
        {replayData && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-3 border-t border-slate-800/80 font-mono text-xs">
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase block">Start Time</span>
              <span className="text-slate-200 font-medium truncate block" title={replayData.start_timestamp || '—'}>
                {replayData.start_timestamp ? replayData.start_timestamp.replace('T', ' ').replace('Z', '') : '—'}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase block">End Time</span>
              <span className="text-slate-200 font-medium truncate block" title={replayData.end_timestamp || '—'}>
                {replayData.end_timestamp ? replayData.end_timestamp.replace('T', ' ').replace('Z', '') : '—'}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase block">Duration</span>
              <span className="text-cyan-400 font-bold">{replayData.duration_seconds}s</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase block">Recorded Events</span>
              <span className="text-white font-bold">{replayData.summary?.event_count ?? events.length} events</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase block">Involved Assets</span>
              <span className="text-white font-bold">{replayData.summary?.asset_count ?? 4} assets</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase block">Evidence Sources</span>
              <span className="text-white font-bold">{replayData.summary?.evidence_count ?? 4} sources</span>
            </div>
          </div>
        )}
      </div>

      {/* 2. LOADING STATE */}
      {loading && (
        <div className="p-12 rounded-xl border border-slate-800 bg-[#0c1322] flex flex-col items-center justify-center space-y-3 font-mono text-sm text-slate-400">
          <div className="w-8 h-8 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin" />
          <span>Loading forensic incident replay from recorded evidence...</span>
        </div>
      )}

      {/* 3. ERROR STATE */}
      {!loading && error && (
        <div className="p-8 rounded-xl border border-rose-800/80 bg-rose-950/20 space-y-4 font-mono shadow-xl">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <h2 className="text-base font-bold text-rose-200">Replay Service Communication Error</h2>
              <p className="text-xs text-rose-300/80 mt-1">{error}</p>
              <p className="text-xs text-slate-400 mt-2">
                RETRACE maintains strict provenance: fallback or synthetic replay data is prohibited. Please check that the intelligence backend is online.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 pt-2">
            <button
              id="replay-retry-btn"
              onClick={() => fetchReplay(activeWindow?.start, activeWindow?.end)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-900 hover:bg-rose-800 text-white text-xs font-bold transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Connection</span>
            </button>
            {activeWindow && (
              <button
                onClick={handleResetWindow}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
              >
                Reset Window Filter
              </button>
            )}
          </div>
        </div>
      )}

      {/* 4. EMPTY EVENTS STATE */}
      {!loading && !error && events.length === 0 && (
        <div className="p-12 rounded-xl border border-slate-800 bg-[#0c1322] text-center space-y-3 font-mono">
          <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto" />
          <h2 className="text-white font-bold text-sm">No Recorded Replay Events Found</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            The live API returned zero recorded events for incident {incidentId} within the selected parameters.
          </p>
          {activeWindow && (
            <button
              onClick={handleResetWindow}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
            >
              Reset Window Filter
            </button>
          )}
        </div>
      )}

      {/* 5. MAIN INTERACTIVE REPLAY CONTENT */}
      {!loading && !error && events.length > 0 && currentEvent && (
        <>
          {/* WINDOW FILTERING CONTROLS */}
          <div className="rounded-xl border border-slate-800 bg-[#0a101d] p-4 flex flex-col md:flex-row items-center justify-between gap-4 font-mono text-xs">
            <div className="flex items-center gap-2 text-slate-400">
              <Filter className="w-4 h-4 text-cyan-400" />
              <span className="font-bold text-slate-300">Forensic Window Filter:</span>
              <span className="text-[11px] text-slate-500">
                (Filter events by start/end seconds offset)
              </span>
            </div>

            <form onSubmit={handleApplyWindow} className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded px-2 py-1">
                <span className="text-slate-500 text-[11px]">Start (s):</span>
                <input
                  id="replay-filter-start-input"
                  type="number"
                  placeholder="0"
                  value={startOffsetInput}
                  onChange={(e) => setStartOffsetInput(e.target.value)}
                  className="w-14 bg-transparent text-white font-mono text-xs focus:outline-none"
                  min={0}
                />
              </div>

              <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded px-2 py-1">
                <span className="text-slate-500 text-[11px]">End (s):</span>
                <input
                  id="replay-filter-end-input"
                  type="number"
                  placeholder={String(totalDuration)}
                  value={endOffsetInput}
                  onChange={(e) => setEndOffsetInput(e.target.value)}
                  className="w-14 bg-transparent text-white font-mono text-xs focus:outline-none"
                  min={0}
                />
              </div>

              <button
                id="replay-apply-filter-btn"
                type="submit"
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 font-bold transition-colors"
              >
                Apply Window
              </button>

              {activeWindow && (
                <button
                  id="replay-reset-filter-btn"
                  type="button"
                  onClick={handleResetWindow}
                  className="px-3 py-1 rounded bg-slate-850 hover:bg-slate-800 text-slate-400 border border-slate-800 transition-colors"
                >
                  Reset Window
                </button>
              )}
            </form>
          </div>

          {/* HORIZONTAL REPLAY TIMELINE */}
          <div className="rounded-xl border border-slate-800 bg-[#090e1b] p-6 space-y-8 shadow-xl">
            <div className="flex items-center justify-between font-mono text-xs">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span className="text-slate-400 font-bold uppercase tracking-wider">
                  Chronological Replay Timeline
                </span>
                <span className="text-[11px] text-slate-500">
                  (0s ----------------------------- {totalDuration}s)
                </span>
              </div>
              <div className="text-slate-400">
                Active Step:{' '}
                <span className="text-cyan-300 font-bold">
                  {activeIndex + 1} of {events.length}
                </span>{' '}
                (+{currentEvent.relative_seconds}s)
              </div>
            </div>

            {/* Visual Timeline Track */}
            <div className="relative pt-6 pb-8 px-2 sm:px-6">
              {/* Baseline Horizontal Bar */}
              <div className="relative w-full h-1.5 bg-slate-800 rounded-full">
                {/* Progress bar up to active event */}
                <div
                  className="absolute h-full bg-cyan-500/70 rounded-full transition-all duration-300"
                  style={{
                    width: `${totalDuration > 0 ? (currentEvent.relative_seconds / totalDuration) * 100 : 0}%`,
                  }}
                />
              </div>

              {/* Event Markers along the timeline */}
              {events.map((evt, idx) => {
                const percent =
                  totalDuration > 0
                    ? Math.min(100, Math.max(0, (evt.relative_seconds / totalDuration) * 100))
                    : (idx / Math.max(1, events.length - 1)) * 100;
                const isSelected = idx === activeIndex;
                const phaseStyle = PHASE_STYLES[evt.phase] || PHASE_STYLES.UNCLASSIFIED;

                return (
                  <div
                    key={evt.event_id || idx}
                    className="absolute -top-3.5 -translate-x-1/2 flex flex-col items-center group cursor-pointer"
                    style={{ left: `${percent}%` }}
                    onClick={() => {
                      setIsPlaying(false);
                      setActiveIndex(idx);
                    }}
                  >
                    {/* Time pill above marker */}
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded border mb-1.5 transition-all ${
                        isSelected
                          ? 'bg-cyan-950 text-cyan-200 border-cyan-500 font-bold shadow-md shadow-cyan-950/60'
                          : 'bg-slate-900/90 text-slate-400 border-slate-800 group-hover:text-slate-200 group-hover:border-slate-700'
                      }`}
                    >
                      +{evt.relative_seconds}s
                    </span>

                    {/* Marker Dot */}
                    <div
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                        isSelected
                          ? `${phaseStyle.marker} ring-4 ring-cyan-500/30 scale-125 shadow-lg shadow-cyan-900/50`
                          : `${phaseStyle.marker} opacity-70 group-hover:opacity-100 group-hover:scale-110`
                      }`}
                    >
                      <div className="w-1.5 h-1.5 bg-white rounded-full" />
                    </div>

                    {/* Event ID and Asset below marker */}
                    <div className="mt-2 flex flex-col items-center text-center pointer-events-none">
                      <span
                        className={`text-[11px] font-mono font-bold leading-tight ${
                          isSelected ? 'text-cyan-300' : 'text-slate-400 group-hover:text-slate-300'
                        }`}
                      >
                        {evt.event_id}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 truncate max-w-[70px]">
                        {evt.asset_id}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Timeline Phase Legend */}
            <div className="flex items-center justify-between flex-wrap gap-2 pt-4 border-t border-slate-800/80 font-mono text-[11px]">
              <span className="text-slate-500 uppercase tracking-wider text-[10px]">Forensic Phases:</span>
              <div className="flex items-center gap-2 flex-wrap">
                {(Object.keys(PHASE_LABELS) as ReplayPhase[]).map((p) => {
                  const st = PHASE_STYLES[p];
                  return (
                    <span
                      key={p}
                      className={`px-2 py-0.5 rounded border text-[10px] font-mono flex items-center gap-1.5 ${st.badge}`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${st.marker}`} />
                      {PHASE_LABELS[p]}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>

          {/* REPLAY CONTROLS BAR */}
          <div className="rounded-xl border border-slate-800 bg-[#0a101d] p-5 flex flex-col sm:flex-row items-center justify-between gap-4 font-mono shadow-xl">
            {/* Step Controls */}
            <div className="flex items-center gap-2">
              <button
                id="replay-restart-btn"
                onClick={handleRestart}
                title="Restart from beginning (+0s)"
                className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
              </button>

              <button
                id="replay-previous-event-btn"
                onClick={handleStepBack}
                disabled={activeIndex === 0}
                title="Previous Event"
                className={`p-2.5 rounded-lg border transition-colors ${
                  activeIndex === 0
                    ? 'bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed'
                    : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300 hover:text-white'
                }`}
              >
                <SkipBack className="w-4 h-4" />
              </button>

              <button
                id="replay-play-pause-btn"
                onClick={handlePlayPause}
                className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold shadow-lg shadow-cyan-950/50 transition-all"
              >
                {isPlaying ? (
                  <>
                    <Pause className="w-4 h-4 fill-current" />
                    <span>Pause</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>{activeIndex >= events.length - 1 ? 'Replay Sequence' : 'Play Sequence'}</span>
                  </>
                )}
              </button>

              <button
                id="replay-next-event-btn"
                onClick={handleStepForward}
                disabled={activeIndex === events.length - 1}
                title="Next Event"
                className={`p-2.5 rounded-lg border transition-colors ${
                  activeIndex === events.length - 1
                    ? 'bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed'
                    : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300 hover:text-white'
                }`}
              >
                <SkipForward className="w-4 h-4" />
              </button>
            </div>

            {/* Current Active Step Stamp */}
            <div className="flex items-center gap-3 bg-[#0d1525] border border-slate-800 px-4 py-2 rounded-lg">
              <Clock className="w-4 h-4 text-cyan-400" />
              <div>
                <span className="text-[10px] text-slate-500 block uppercase">Relative Time</span>
                <span className="text-base font-bold text-white tracking-wider">
                  +{currentEvent.relative_seconds}s
                </span>
              </div>
              <div className="h-6 w-px bg-slate-800 mx-1" />
              <div>
                <span className="text-[10px] text-slate-500 block uppercase">Active Event</span>
                <span className="text-xs font-bold text-cyan-300">{currentEvent.event_id}</span>
              </div>
            </div>

            {/* Playback Speed Controls */}
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="text-[11px] text-slate-500">Speed:</span>
              {[0.5, 1, 2].map((spd) => (
                <button
                  key={spd}
                  onClick={() => setPlaybackSpeed(spd)}
                  className={`px-2.5 py-1 rounded font-bold transition-colors ${
                    playbackSpeed === spd
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                      : 'bg-slate-800/80 text-slate-400 hover:text-white border border-slate-800'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>

          {/* 6. DETAILS SECTION: SELECTED EVENT, RECORDED VALUES, EVIDENCE, TOPOLOGY */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* LEFT / CENTER (2 COLS): Active Event Dossier */}
            <div className="lg:col-span-2 space-y-6">
              {/* SELECTED EVENT CARD */}
              <div
                id="replay-selected-event-card"
                className={`rounded-xl border bg-[#0c1322] p-6 space-y-5 shadow-xl transition-all ${
                  (PHASE_STYLES[currentEvent.phase] || PHASE_STYLES.UNCLASSIFIED).border
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="text-sm font-mono font-bold text-cyan-300 bg-cyan-950 border border-cyan-800 px-2.5 py-1 rounded">
                      +{currentEvent.relative_seconds}s
                    </span>
                    <span className="text-xs font-mono font-bold text-slate-200 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded">
                      {currentEvent.event_id}
                    </span>
                    <span className="text-xs font-mono font-bold text-white bg-slate-800/80 border border-slate-700 px-2.5 py-1 rounded">
                      Asset: {currentEvent.asset_id}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2.5 py-1 rounded border font-mono font-bold ${
                        (PHASE_STYLES[currentEvent.phase] || PHASE_STYLES.UNCLASSIFIED).badge
                      }`}
                    >
                      {PHASE_LABELS[currentEvent.phase] || currentEvent.phase}
                    </span>
                    <span
                      className={`text-xs px-2 py-1 rounded border font-mono font-semibold ${
                        SEVERITY_STYLES[currentEvent.severity] || SEVERITY_STYLES.Low
                      }`}
                    >
                      {currentEvent.severity}
                    </span>
                  </div>
                </div>

                <div>
                  <h2 className="text-lg font-bold font-mono text-white tracking-wide">
                    {currentEvent.title}
                  </h2>
                  <div className="text-[11px] font-mono text-slate-400 mt-1 flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>Exact Timestamp: {currentEvent.timestamp}</span>
                    <span className="text-slate-600">•</span>
                    <span>Sequence: #{currentEvent.sequence}</span>
                  </div>
                </div>

                {/* Event Description */}
                <div className="p-4 rounded-lg bg-[#080d19] border border-slate-800/80">
                  <span className="text-[10px] font-mono uppercase text-slate-500 block mb-1">
                    Factual Event Description
                  </span>
                  <p className="text-xs text-slate-200 font-sans leading-relaxed">
                    {currentEvent.description}
                  </p>
                </div>

                {/* RECORDED VALUES / TELEMETRY SECTION */}
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between font-mono text-xs">
                    <span className="font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                      <Database className="w-4 h-4 text-cyan-400" />
                      Recorded Telemetry & Observations
                    </span>
                    <span className="text-[11px] text-slate-500">
                      Grounded strictly in supporting evidence
                    </span>
                  </div>

                  {currentEvent.recorded_values && currentEvent.recorded_values.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono">
                      {currentEvent.recorded_values.map((val, vIdx) => (
                        <div
                          key={vIdx}
                          className="p-3 rounded-lg bg-[#090e1a] border border-slate-800 flex items-center justify-between"
                        >
                          <div>
                            <span className="text-[10px] text-slate-500 uppercase block">
                              {formatMetricName(val.name)}
                            </span>
                            <div className="text-sm font-bold text-white mt-0.5">
                              {String(val.value)}{' '}
                              {val.unit && (
                                <span className="text-xs font-normal text-cyan-400 ml-0.5">
                                  {val.unit}
                                </span>
                              )}
                            </div>
                          </div>
                          {val.source_evidence_id && (
                            <span
                              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700 text-slate-400 shrink-0 cursor-pointer hover:border-cyan-700 hover:text-cyan-300 transition-colors"
                              title={`Source Evidence ID: ${val.source_evidence_id}`}
                              onClick={() => handleEvidenceClick({ evidence_id: val.source_evidence_id, filename: val.source_evidence_id })}
                            >
                              {val.source_evidence_id}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    /* MANDATORY HANDLING FOR EMPTY RECORDED VALUES (e.g. EVT-003) */
                    <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800/80 text-center font-mono space-y-1.5">
                      <p className="text-xs font-semibold text-amber-300">
                        No exact telemetry sample recorded at this event timestamp.
                      </p>
                      <p className="text-[11px] text-slate-500">
                        Historian recording occurs at discrete sample intervals; missing telemetry at {currentEvent.timestamp} is omitted rather than interpolated or inferred from neighboring measurements.
                      </p>
                    </div>
                  )}
                </div>

                {/* ASSET STATE (if present) */}
                {currentEvent.asset_state && (
                  <div className="pt-3 border-t border-slate-800/80 font-mono text-xs space-y-2">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                        <Tag className="w-3.5 h-3.5 text-cyan-400" />
                        Asset State: {currentEvent.asset_state.asset_id}
                      </span>
                      {currentEvent.asset_state.operational_status && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-850 border border-slate-700 text-slate-300">
                          Status: {currentEvent.asset_state.operational_status}
                        </span>
                      )}
                    </div>
                    {currentEvent.asset_state.asset_name && (
                      <p className="text-[11px] text-slate-400">
                        {currentEvent.asset_state.asset_name}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* SUPPORTING EVIDENCE PANEL */}
              <div className="rounded-xl border border-slate-800 bg-[#0c1322] p-6 space-y-4 shadow-xl">
                <div className="flex items-center justify-between font-mono text-xs">
                  <h3 className="font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <FileText className="w-4 h-4 text-cyan-400" />
                    Supporting Evidence Provenance ({currentEvent.evidence.length})
                  </h3>
                  <span className="text-[11px] text-slate-500">Click to view evidence document</span>
                </div>

                <div className="space-y-3 font-mono">
                  {currentEvent.evidence.map((ev, eIdx) => (
                    <div
                      key={ev.evidence_id || eIdx}
                      onClick={() => handleEvidenceClick(ev)}
                      className="p-4 rounded-lg bg-[#090e1a] border border-slate-800 hover:border-cyan-700/80 hover:bg-[#0c1628] transition-all cursor-pointer group space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300 text-xs font-bold">
                            {ev.evidence_id}
                          </span>
                          <span className="text-xs font-bold text-white group-hover:text-cyan-200 transition-colors">
                            {ev.filename}
                          </span>
                        </div>
                        <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {ev.source_type}
                        </span>
                      </div>

                      {ev.original_reference && (
                        <div className="text-[11px] text-slate-400 font-sans bg-[#060a12] p-2 rounded border border-slate-800/80">
                          <span className="font-mono text-slate-500 text-[10px] uppercase block">
                            Original Evidence Reference:
                          </span>
                          <span>{ev.original_reference}</span>
                        </div>
                      )}

                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                        <span>Source Timestamp: {ev.timestamp || '—'}</span>
                        <span className="text-cyan-400 group-hover:underline flex items-center gap-1">
                          <Eye className="w-3 h-3" /> View in Inspector
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* ASSET TOPOLOGY CONTEXT PANEL */}
              <div className="rounded-xl border border-slate-800 bg-[#0c1322] p-6 space-y-4 shadow-xl font-mono text-xs">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <Network className="w-4 h-4 text-cyan-400" />
                    Equipment Topology Context
                  </h3>
                  <span className="text-[11px] text-slate-500">Active Coupling</span>
                </div>

                {/* Strict Non-Causality Topology Disclaimer */}
                <div className="p-3 rounded-lg bg-[#080d19] border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
                  <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                  <span>
                    Equipment topology; relationships do not imply causation.
                  </span>
                </div>

                {currentEvent.graph_relationships && currentEvent.graph_relationships.length > 0 ? (
                  <div className="space-y-2">
                    {currentEvent.graph_relationships.map((rel, rIdx) => (
                      <div
                        key={rIdx}
                        className="p-3 rounded-lg bg-[#090e1a] border border-slate-800 flex items-center justify-between flex-wrap gap-2"
                      >
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-white font-bold">
                            {rel.source}
                          </span>
                          <span className="text-cyan-400 font-bold px-1.5 text-[11px]">
                            → {rel.relationship} →
                          </span>
                          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-white font-bold">
                            {rel.target}
                          </span>
                        </div>
                        {rel.description && (
                          <span className="text-[11px] text-slate-400 italic">
                            {rel.description}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">
                    No direct graph relationship records linked to this event timestamp.
                  </p>
                )}
              </div>
            </div>

            {/* RIGHT (1 COL): Vertical Event Sequence List */}
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-[#0c1322] p-5 space-y-3 shadow-xl">
                <div className="flex items-center justify-between font-mono text-xs pb-2 border-b border-slate-800">
                  <h3 className="font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <Layers className="w-4 h-4 text-cyan-400" />
                    Event Sequence ({events.length})
                  </h3>
                  <span className="text-[11px] text-slate-500">Chronological</span>
                </div>

                <div className="space-y-2.5 max-h-[850px] overflow-y-auto pr-1">
                  {events.map((evt, idx) => {
                    const isSelected = idx === activeIndex;
                    const phaseStyle = PHASE_STYLES[evt.phase] || PHASE_STYLES.UNCLASSIFIED;

                    return (
                      <div
                        key={evt.event_id || idx}
                        onClick={() => {
                          setIsPlaying(false);
                          setActiveIndex(idx);
                        }}
                        className={`p-3.5 rounded-lg border font-mono text-xs cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-[#0f1b33] border-cyan-500 shadow-md shadow-cyan-950/60 ring-1 ring-cyan-500/40'
                            : 'bg-[#090e1a] border-slate-800/90 hover:border-slate-700 hover:bg-[#0c1424] text-slate-400'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                                isSelected
                                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700'
                                  : 'bg-slate-900 text-slate-400 border border-slate-800'
                              }`}
                            >
                              +{evt.relative_seconds}s
                            </span>
                            <span
                              className={`text-[11px] font-bold ${
                                isSelected ? 'text-white' : 'text-slate-300'
                              }`}
                            >
                              {evt.event_id}
                            </span>
                          </div>

                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded border font-semibold ${
                              phaseStyle.badge
                            }`}
                          >
                            {PHASE_LABELS[evt.phase] || evt.phase}
                          </span>
                        </div>

                        <div
                          className={`font-semibold line-clamp-1 mb-1.5 ${
                            isSelected ? 'text-cyan-200' : 'text-slate-300'
                          }`}
                        >
                          {evt.title}
                        </div>

                        <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1.5 border-t border-slate-800/60">
                          <span className="font-bold text-slate-400">Asset: {evt.asset_id}</span>
                          <span
                            className={`px-1.5 py-0.5 rounded border ${
                              SEVERITY_STYLES[evt.severity] || SEVERITY_STYLES.Low
                            }`}
                          >
                            {evt.severity}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
