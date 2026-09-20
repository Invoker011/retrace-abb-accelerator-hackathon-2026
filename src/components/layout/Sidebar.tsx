import React from 'react';
import {
  LayoutDashboard,
  AlertTriangle,
  MessageSquareCode,
  PlaySquare,
  Network,
  Files,
  ShieldAlert,
  ShieldCheck,
  Radio,
} from 'lucide-react';

export type NavView =
  | 'dashboard'
  | 'incidents'
  | 'investigation'
  | 'replay'
  | 'graph'
  | 'evidence'
  | 'prevention';

interface SidebarProps {
  activeView: NavView;
  onNavigate: (view: NavView) => void;
  activeIncidentId?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  onNavigate,
  activeIncidentId = 'INC-2026-001',
}) => {
  const navItems: Array<{
    id: NavView;
    label: string;
    icon: React.ReactNode;
    badge?: string;
  }> = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: <LayoutDashboard className="w-4 h-4" />,
    },
    {
      id: 'incidents',
      label: 'Incidents',
      icon: <AlertTriangle className="w-4 h-4" />,
      badge: '1 Active',
    },
    {
      id: 'investigation',
      label: 'Investigation',
      icon: <MessageSquareCode className="w-4 h-4" />,
      badge: 'Grounded',
    },
    {
      id: 'replay',
      label: 'Incident Replay',
      icon: <PlaySquare className="w-4 h-4" />,
    },
    {
      id: 'graph',
      label: 'Context Graph',
      icon: <Network className="w-4 h-4" />,
    },
    {
      id: 'evidence',
      label: 'Evidence',
      icon: <Files className="w-4 h-4" />,
      badge: '6 Sources',
    },
    {
      id: 'prevention',
      label: 'What Could Have Prevented It?',
      icon: <ShieldAlert className="w-4 h-4" />,
      badge: 'Counterfactual',
    },
  ];

  return (
    <aside
      id="retrace-sidebar"
      className="w-72 bg-[#080d17] border-r border-slate-800/80 flex flex-col justify-between select-none h-screen sticky top-0 shrink-0 z-30"
    >
      {/* Top Branding Section */}
      <div>
        <div className="p-5 border-b border-slate-800/80 bg-[#0a101d]/60">
          <div className="mb-1">
            <div className="flex items-center justify-between">
              <div className="font-mono text-xl font-bold tracking-wider text-white uppercase inline-flex items-baseline">
                <span>RETR</span>
                <span className="text-[#FF1A1A] font-extrabold">A</span>
                <span>CE</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 font-mono">
                v0.1
              </span>
            </div>
            <p className="text-[11px] font-mono tracking-wide text-slate-300 font-medium uppercase mt-0.5">
              Industrial Incident Forensics
            </p>
            <p className="text-[11px] font-mono tracking-wide text-cyan-400/90 font-medium mt-0.5">
              Reconstruct. Replay. Learn.
            </p>
          </div>
          <div className="mt-3 flex items-center gap-2 text-[11px] font-mono text-slate-400 bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
            <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
            <span className="truncate">Active: <span className="text-slate-200 font-semibold">{activeIncidentId}</span></span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          <div className="px-3 py-1.5 text-[11px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Investigation Modules
          </div>
          {navItems.map((item, index) => {
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                  isActive
                    ? 'bg-cyan-950/40 text-cyan-300 border border-cyan-800/60 shadow-sm shadow-cyan-950/50'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`transition-colors ${
                      isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-300'
                    }`}
                  >
                    {item.icon}
                  </span>
                  <span className="truncate text-left">{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      isActive
                        ? 'bg-cyan-900/60 text-cyan-300 border border-cyan-700/50'
                        : 'bg-slate-800/80 text-slate-400'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Safety & Non-Actuation Disclaimer Footer */}
      <div className="p-4 border-t border-slate-800/80 bg-[#070b14]/80 text-[11px] font-mono text-slate-400 space-y-2">
        <div className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[10px] uppercase tracking-wider">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Non-Actuating Safety Layer</span>
        </div>
        <p className="text-slate-400 text-[11px] leading-tight">
          Advisory intelligence only. RETRACE never issues live control, override, or actuation commands to plant machinery.
        </p>
        <div className="pt-1 text-[10px] text-slate-400 flex items-center justify-between border-t border-slate-800/50">
          <span>ABB Hackathon 2026</span>
          <span className="text-cyan-500">Theme 2</span>
        </div>
      </div>
    </aside>
  );
};
