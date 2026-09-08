import React from 'react';
import {
  Activity,
  Clock,
  MapPin,
  Shield,
  Layers,
  Server,
} from 'lucide-react';
import { Incident } from '../../types';
import { ApiConnectionState } from '../../services/apiClient';

interface HeaderProps {
  currentIncident: Incident;
  onNavigateToView: (view: 'incidents' | 'replay' | 'evidence') => void;
  apiStatus?: ApiConnectionState;
}

export const Header: React.FC<HeaderProps> = ({
  currentIncident,
  onNavigateToView,
  apiStatus = 'connecting',
}) => {
  return (
    <header
      id="retrace-header"
      className="h-16 border-b border-slate-800/80 bg-[#090e1a]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20"
    >
      {/* Plant Area & Active Context */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-300 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-md">
          <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span className="font-semibold text-white">{currentIncident.plantArea}</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">Train B Slurry Skid</span>
        </div>

        <div className="hidden lg:flex items-center gap-2 text-xs font-mono">
          <span className="text-slate-500">Incident Context:</span>
          <button
            onClick={() => onNavigateToView('incidents')}
            className="text-cyan-300 font-semibold hover:underline flex items-center gap-1.5 px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/40"
          >
            <span>{currentIncident.id}</span>
            <span className="text-slate-400 font-normal">({currentIncident.title})</span>
          </button>
        </div>
      </div>

      {/* Right Telemetry & Status Badges */}
      <div className="flex items-center gap-3">
        {/* Backend API Connection Indicator */}
        <div
          id="api-connection-status"
          className={`flex items-center gap-1.5 text-xs font-mono px-2.5 py-1.5 rounded-md border transition-colors ${
            apiStatus === 'live'
              ? 'bg-emerald-950/50 border-emerald-800/60 text-emerald-300'
              : apiStatus === 'mock_fallback'
              ? 'bg-amber-950/50 border-amber-800/60 text-amber-300'
              : 'bg-slate-900/60 border-slate-800/70 text-slate-400'
          }`}
          title={
            apiStatus === 'live'
              ? 'FastAPI intelligence backend connected and healthy'
              : apiStatus === 'mock_fallback'
              ? 'Backend unreachable or CORS blocked - using synthetic mock data fallback'
              : 'Verifying backend connection...'
          }
        >
          <span
            className={`w-2 h-2 rounded-full ${
              apiStatus === 'live'
                ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]'
                : apiStatus === 'mock_fallback'
                ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]'
                : 'bg-slate-400 animate-pulse'
            }`}
          />
          <span className="font-semibold text-[11px] tracking-wide">
            {apiStatus === 'live'
              ? 'API: LIVE'
              : apiStatus === 'mock_fallback'
              ? 'API: MOCK FALLBACK'
              : 'API: CONNECTING'}
          </span>
        </div>

        {/* Synthetic Time Synchronization */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs font-mono text-slate-400 bg-slate-900/60 border border-slate-800/70 px-2.5 py-1.5 rounded-md">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Incident T₀: <span className="text-slate-200">10:14:01</span></span>
        </div>

        {/* Severity Badge */}
        <div className="flex items-center gap-1.5 text-xs font-mono px-2.5 py-1.5 rounded-md bg-rose-950/40 border border-rose-800/50 text-rose-400 font-semibold">
          <Activity className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
          <span>Severity: HIGH</span>
        </div>

        {/* Advisory Guardrail Badge */}
        <div className="flex items-center gap-1.5 text-xs font-mono px-2.5 py-1.5 rounded-md bg-cyan-950/40 border border-cyan-800/40 text-cyan-400">
          <Shield className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Decision Support</span>
          <span className="text-[10px] bg-cyan-900/70 text-cyan-200 px-1 py-0.2 rounded font-bold">
            GROUNDED
          </span>
        </div>
      </div>
    </header>
  );
};
