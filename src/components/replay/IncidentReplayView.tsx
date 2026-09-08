import React, { useState, useEffect, useRef } from 'react';
import {
  IncidentEvent,
  Asset,
} from '../../types';
import {
  Play,
  Pause,
  RotateCcw,
  SkipBack,
  SkipForward,
  Activity,
  Zap,
  Gauge,
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ChevronDown,
} from 'lucide-react';

interface IncidentReplayViewProps {
  events: IncidentEvent[];
  assets: Asset[];
}

export const IncidentReplayView: React.FC<IncidentReplayViewProps> = ({ events, assets }) => {
  // Timeline runs from 0 to 30 seconds (10:14:00 to 10:14:30)
  const MAX_SECONDS = 30;
  const [currentSecond, setCurrentSecond] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1); // 1x, 2x, 5x
  const timerRef = useRef<any>(null);

  // Playback timer effect
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setCurrentSecond((prev) => {
          if (prev >= MAX_SECONDS) {
            setIsPlaying(false);
            return MAX_SECONDS;
          }
          return prev + 1;
        });
      }, 1000 / playbackSpeed);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, playbackSpeed]);

  const handlePlayPause = () => {
    if (currentSecond >= MAX_SECONDS) {
      setCurrentSecond(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleRestart = () => {
    setIsPlaying(false);
    setCurrentSecond(0);
  };

  const handleStepBack = () => {
    setIsPlaying(false);
    setCurrentSecond((prev) => Math.max(0, prev - 1));
  };

  const handleStepForward = () => {
    setIsPlaying(false);
    setCurrentSecond((prev) => Math.min(MAX_SECONDS, prev + 1));
  };

  // Convert currentSecond into synthetic clock: 10:14:00 + second
  const formatReplayTime = (sec: number) => {
    const padded = sec.toString().padStart(2, '0');
    return `10:14:${padded}`;
  };

  // Determine asset highlight state based on the 4 key stages:
  // Step 1: VFD-204 triggers at t >= 1s
  // Step 2: Motor M-204 triggers at t >= 5s
  // Step 3: Pump P-204 triggers at t >= 12s (and vibration report at t >= 18s)
  // Step 4: PLC Alarm triggers at t >= 28s
  const isVfdActive = currentSecond >= 1;
  const isMotorActive = currentSecond >= 5;
  const isPumpActive = currentSecond >= 12;
  const isPlcActive = currentSecond >= 28;

  // Real-time simulated telemetry curves matching timeline:
  const getCurrentA = () => {
    if (currentSecond < 1) return 194.2;
    if (currentSecond <= 3) return 268.4;
    if (currentSecond <= 10) return 252.1;
    if (currentSecond < 28) return 248.0;
    return 0.0; // Tripped
  };

  const getPressureBar = () => {
    if (currentSecond < 10) return 6.8;
    if (currentSecond < 15) return 5.4;
    if (currentSecond < 20) return 4.2;
    if (currentSecond < 28) return 3.8;
    return 1.1; // Tripped
  };

  const getVibrationMmS = () => {
    if (currentSecond < 5) return 2.1;
    if (currentSecond < 12) return 3.8;
    if (currentSecond < 18) return 5.9;
    if (currentSecond < 28) return 8.4;
    return 9.2; // Tripped peak
  };

  const getActiveEvents = () => {
    return events.filter((evt) => evt.relativeSeconds <= currentSecond);
  };

  const currentActiveEvent = events
    .slice()
    .reverse()
    .find((evt) => evt.relativeSeconds <= currentSecond);

  return (
    <div id="incident-replay-view" className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Top Replay Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">
              Deterministic Cascade Reconstruction
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300 font-mono">
              Temporal Step Analysis
            </span>
          </div>
          <h1 className="text-2xl font-bold font-mono text-white mt-1">
            Incident Telemetry Replay Engine
          </h1>
          <p className="text-xs text-slate-400 font-sans">
            Playback the 27-second propagation cascade: VFD-204 → Motor M-204 → Pump P-204 → PLC Trip
          </p>
        </div>

        {/* Current Replay Clock Display */}
        <div className="flex items-center gap-3 bg-[#0c1322] border border-slate-800 px-4 py-2.5 rounded-xl font-mono">
          <Clock className="w-5 h-5 text-cyan-400 animate-pulse" />
          <div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Normalized Replay Time</div>
            <div className="text-lg font-bold text-white tracking-wider">
              {formatReplayTime(currentSecond)}{' '}
              <span className="text-xs font-normal text-cyan-400">
                (+{currentSecond}s)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Cascade Visualization: VFD-204 -> Motor M-204 -> Pump P-204 -> PLC Alarm */}
      <div className="rounded-xl border border-slate-800 bg-[#090e1b] p-6 space-y-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            Asset Propagation Pipeline
          </h2>
          <span className="text-xs font-mono text-slate-500">
            Current Stage:{' '}
            <span className="text-cyan-300 font-bold">
              {isPlcActive
                ? 'STAGE 4: SCADA INTERLOCK TRIP'
                : isPumpActive
                ? 'STAGE 3: PUMP PRESSURE DISTURBANCE'
                : isMotorActive
                ? 'STAGE 2: MOTOR PHASE DEVIATION'
                : isVfdActive
                ? 'STAGE 1: VFD OVERCURRENT WARNING'
                : 'NORMAL STEADY STATE'}
            </span>
          </span>
        </div>

        {/* 4 Connected Asset Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
          {/* Card 1: VFD-204 */}
          <div
            className={`p-4 rounded-xl border transition-all duration-300 relative ${
              isVfdActive
                ? 'bg-amber-950/30 border-amber-500/80 shadow-lg shadow-amber-950/40 ring-1 ring-amber-500/50'
                : 'bg-slate-900/40 border-slate-800 text-slate-400'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase text-slate-400">Step 1 • 10:14:01 (+0s)</span>
              <Zap
                className={`w-4 h-4 ${
                  isVfdActive ? 'text-amber-400 animate-bounce' : 'text-slate-600'
                }`}
              />
            </div>
            <div className="font-mono text-base font-bold text-white">VFD-204</div>
            <div className="text-xs text-slate-400 font-mono">Inverter Drive</div>
            <div className="mt-3 pt-3 border-t border-slate-800/80 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-500">Current:</span>
                <span className={`font-bold ${isVfdActive ? 'text-amber-400' : 'text-slate-300'}`}>
                  {getCurrentA()} A
                </span>
              </div>
              <div className="text-[11px] mt-1 text-slate-400 truncate">
                {isVfdActive ? '⚠️ Overcurrent W-2310' : 'Normal 194A'}
              </div>
            </div>
          </div>

          {/* Card 2: Motor M-204 */}
          <div
            className={`p-4 rounded-xl border transition-all duration-300 relative ${
              isMotorActive
                ? 'bg-amber-950/30 border-amber-500/80 shadow-lg shadow-amber-950/40 ring-1 ring-amber-500/50'
                : 'bg-slate-900/40 border-slate-800 text-slate-400'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase text-slate-400">Step 2 • 10:14:05 (+4s)</span>
              <Activity
                className={`w-4 h-4 ${
                  isMotorActive ? 'text-amber-400 animate-pulse' : 'text-slate-600'
                }`}
              />
            </div>
            <div className="font-mono text-base font-bold text-white">Motor M-204</div>
            <div className="text-xs text-slate-400 font-mono">110kW Induction</div>
            <div className="mt-3 pt-3 border-t border-slate-800/80 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-500">Imbalance:</span>
                <span className={`font-bold ${isMotorActive ? 'text-amber-400' : 'text-slate-300'}`}>
                  {isMotorActive ? '8.2% Deviation' : '< 1.0% Balanced'}
                </span>
              </div>
              <div className="text-[11px] mt-1 text-slate-400 truncate">
                {isMotorActive ? '⚠️ Phase Current Ripple' : 'Normal Sync Speed'}
              </div>
            </div>
          </div>

          {/* Card 3: Pump P-204 */}
          <div
            className={`p-4 rounded-xl border transition-all duration-300 relative ${
              isPumpActive
                ? 'bg-rose-950/40 border-rose-500/80 shadow-lg shadow-rose-950/40 ring-1 ring-rose-500/50'
                : 'bg-slate-900/40 border-slate-800 text-slate-400'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase text-slate-400">Step 3 • 10:14:12 (+11s)</span>
              <Gauge
                className={`w-4 h-4 ${
                  isPumpActive ? 'text-rose-400 animate-pulse' : 'text-slate-600'
                }`}
              />
            </div>
            <div className="font-mono text-base font-bold text-white">Pump P-204</div>
            <div className="text-xs text-slate-400 font-mono">Booster Centrifugal</div>
            <div className="mt-3 pt-3 border-t border-slate-800/80 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-500">Discharge:</span>
                <span className={`font-bold ${isPumpActive ? 'text-rose-400' : 'text-slate-300'}`}>
                  {getPressureBar()} bar
                </span>
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-slate-500">Vibration:</span>
                <span className={`font-bold ${getVibrationMmS() > 7.1 ? 'text-rose-400' : getVibrationMmS() > 4.5 ? 'text-amber-400' : 'text-slate-300'}`}>
                  {getVibrationMmS()} mm/s
                </span>
              </div>
            </div>
          </div>

          {/* Card 4: PLC Alarm */}
          <div
            className={`p-4 rounded-xl border transition-all duration-300 relative ${
              isPlcActive
                ? 'bg-rose-950/50 border-rose-500 shadow-xl shadow-rose-950/60 ring-2 ring-rose-500'
                : 'bg-slate-900/40 border-slate-800 text-slate-400'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase text-slate-400">Step 4 • 10:14:28 (+27s)</span>
              <ShieldAlert
                className={`w-4 h-4 ${
                  isPlcActive ? 'text-rose-400 animate-ping' : 'text-slate-600'
                }`}
              />
            </div>
            <div className="font-mono text-base font-bold text-white">PLC Alarm</div>
            <div className="text-xs text-slate-400 font-mono">Safety Interlock</div>
            <div className="mt-3 pt-3 border-t border-slate-800/80 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-500">Interlock:</span>
                <span className={`font-bold ${isPlcActive ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {isPlcActive ? 'TRIPPED (EMERG)' : 'ARMED / OK'}
                </span>
              </div>
              <div className="text-[11px] mt-1 text-slate-400 truncate">
                {isPlcActive ? 'ALM-P204-TRIP-VIB' : 'Monitoring limits'}
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic Event Callout */}
        {currentActiveEvent && (
          <div className="p-4 rounded-lg bg-[#0d1627] border border-cyan-800/50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="font-mono text-xs font-bold text-cyan-300 bg-cyan-950 border border-cyan-800 px-2 py-1 rounded">
                {currentActiveEvent.displayTime}
              </span>
              <div>
                <span className="text-xs font-mono font-semibold text-white">
                  {currentActiveEvent.title}
                </span>
                <p className="text-xs text-slate-300 font-sans mt-0.5">
                  {currentActiveEvent.description}
                </p>
              </div>
            </div>
            <span className="text-[11px] font-mono text-slate-400 shrink-0 hidden sm:inline">
              Ref: {currentActiveEvent.evidenceRef}
            </span>
          </div>
        )}
      </div>

      {/* Interactive Playback Control Bar */}
      <div className="rounded-xl border border-slate-800 bg-[#0a101d] p-6 space-y-4 shadow-xl">
        {/* Timeline Slider / Scrubber */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>10:14:00 (T₀ - 1s)</span>
            <span className="text-cyan-300 font-bold">
              Position: {currentSecond}s / {MAX_SECONDS}s
            </span>
            <span>10:14:30 (Trip Cutoff)</span>
          </div>

          <div className="relative">
            <input
              id="replay-timeline-slider"
              type="range"
              min={0}
              max={MAX_SECONDS}
              value={currentSecond}
              onChange={(e) => {
                setIsPlaying(false);
                setCurrentSecond(Number(e.target.value));
              }}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />

            {/* Event Markers on Slider */}
            <div className="absolute -bottom-4 left-0 right-0 flex justify-between pointer-events-none font-mono text-[10px] text-slate-500">
              <span style={{ left: `${(1 / MAX_SECONDS) * 100}%` }} className="absolute">
                | 1s (VFD)
              </span>
              <span style={{ left: `${(5 / MAX_SECONDS) * 100}%` }} className="absolute">
                | 5s (Motor)
              </span>
              <span style={{ left: `${(12 / MAX_SECONDS) * 100}%` }} className="absolute">
                | 12s (Pump)
              </span>
              <span style={{ left: `${(18 / MAX_SECONDS) * 100}%` }} className="absolute">
                | 18s (Obs)
              </span>
              <span style={{ left: `${(28 / MAX_SECONDS) * 100}%` }} className="absolute -translate-x-full">
                | 28s (Trip)
              </span>
            </div>
          </div>
        </div>

        {/* Transport Controls */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-800/80">
          <div className="flex items-center gap-2">
            <button
              id="replay-restart-btn"
              onClick={handleRestart}
              title="Restart from beginning"
              className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              id="replay-step-back-btn"
              onClick={handleStepBack}
              title="Step back 1 second"
              className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            <button
              id="replay-play-pause-btn"
              onClick={handlePlayPause}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold shadow-lg shadow-cyan-950/50 transition-all"
            >
              {isPlaying ? (
                <>
                  <Pause className="w-4 h-4 fill-current" />
                  <span>Pause Replay</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>{currentSecond >= MAX_SECONDS ? 'Replay Cascade' : 'Play Timeline'}</span>
                </>
              )}
            </button>
            <button
              id="replay-step-forward-btn"
              onClick={handleStepForward}
              title="Step forward 1 second"
              className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
            >
              <SkipForward className="w-4 h-4" />
            </button>
          </div>

          {/* Speed selector */}
          <div className="flex items-center gap-2 font-mono text-xs text-slate-400">
            <span>Speed:</span>
            {[1, 2, 5].map((speed) => (
              <button
                key={speed}
                onClick={() => setPlaybackSpeed(speed)}
                className={`px-2.5 py-1 rounded font-bold transition-colors ${
                  playbackSpeed === speed
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                    : 'bg-slate-800/80 text-slate-400 hover:text-white'
                }`}
              >
                {speed}x
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
