import React from 'react';
import { PreventionScenario } from '../../types';
import {
  ShieldAlert,
  ArrowRight,
  AlertOctagon,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  Info,
  Layers,
  ArrowDown,
  Clock,
  ShieldCheck,
} from 'lucide-react';

interface PreventionViewProps {
  scenario: PreventionScenario;
}

export const PreventionView: React.FC<PreventionViewProps> = ({ scenario }) => {
  return (
    <div id="prevention-view" className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-widest text-purple-400">
              Counterfactual Analysis
            </span>
            {/* Required Label */}
            <span className="text-xs px-2.5 py-0.5 rounded bg-purple-950 border border-purple-800 text-purple-300 font-mono font-bold">
              Exploratory / Hypothetical Analysis
            </span>
          </div>
          <h1 className="text-2xl font-bold font-mono text-white mt-1">
            What Could Have Prevented It?
          </h1>
          <p className="text-xs text-slate-400 font-sans">
            Comparative scenario simulation exploring early warning barriers and mitigation intervention gates.
          </p>
        </div>
      </div>

      {/* Prominent Required Disclaimer */}
      <div
        id="prevention-disclaimer"
        className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/60 flex items-start gap-3 text-amber-200"
      >
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="text-xs font-mono uppercase font-bold text-amber-300 tracking-wider">
            Exploratory Model Disclaimer
          </span>
          <p className="text-xs sm:text-sm font-sans leading-relaxed text-amber-200/90 font-medium">
            "{scenario.disclaimer}"
          </p>
          <p className="text-[11px] font-mono text-amber-400/80">
            Counterfactual simulations are advisory decision aids and do not constitute absolute causal certainty.
          </p>
        </div>
      </div>

      {/* Side-by-Side Path Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Actual Observed Path */}
        <div className="rounded-xl border border-rose-900/60 bg-[#0c0d18] p-6 space-y-6 shadow-xl relative overflow-hidden">
          <div className="flex items-center justify-between pb-3 border-b border-rose-900/40">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-rose-400" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-rose-300">
                Actual Observed Path
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800">
              Unmitigated Hard Trip
            </span>
          </div>

          <div className="space-y-4">
            {scenario.actualPath.map((step, idx) => (
              <div key={step.step} className="relative">
                <div className="p-4 rounded-lg bg-rose-950/20 border border-rose-800/40 space-y-1.5">
                  <div className="flex items-center justify-between font-mono text-xs">
                    <span className="font-bold text-white flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-rose-950 border border-rose-800 text-rose-300 flex items-center justify-center text-[10px]">
                        {step.step}
                      </span>
                      <span>{step.title}</span>
                    </span>
                    <span className="text-[10px] text-rose-400 font-mono">
                      {step.timeOffset}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 font-sans pl-7">
                    {step.description}
                  </p>
                </div>

                {idx < scenario.actualPath.length - 1 && (
                  <div className="flex justify-center my-1.5">
                    <ArrowDown className="w-4 h-4 text-rose-600/70" />
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="p-3 rounded-lg bg-black/40 border border-rose-900/40 text-[11px] font-mono text-rose-300/80">
            Outcome: Automatic safety shutdown triggered by PLC-204 at 10:14:28. Process train tripped off-line.
          </div>
        </div>

        {/* Possible Intervention Path */}
        <div className="rounded-xl border border-cyan-800/60 bg-[#08111e] p-6 space-y-6 shadow-xl relative overflow-hidden">
          <div className="flex items-center justify-between pb-3 border-b border-cyan-800/40">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-cyan-400" />
              <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-cyan-300">
                Possible Intervention Path
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
              Mitigated Controlled Stop
            </span>
          </div>

          <div className="space-y-4">
            {scenario.interventionPath.map((step, idx) => (
              <div key={step.step} className="relative">
                <div
                  className={`p-4 rounded-lg border space-y-1.5 ${
                    step.status === 'intervention_point'
                      ? 'bg-cyan-950/30 border-cyan-700/60 ring-1 ring-cyan-500/30'
                      : step.status === 'mitigation_outcome'
                      ? 'bg-emerald-950/30 border-emerald-700/60'
                      : 'bg-slate-900/40 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between font-mono text-xs">
                    <span className="font-bold text-white flex items-center gap-2">
                      <span
                        className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                          step.status === 'intervention_point'
                            ? 'bg-cyan-900 text-cyan-200 border border-cyan-700'
                            : step.status === 'mitigation_outcome'
                            ? 'bg-emerald-900 text-emerald-200 border border-emerald-700'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {step.step}
                      </span>
                      <span className="text-cyan-200">{step.title}</span>
                    </span>
                    <span className="text-[10px] text-cyan-400 font-mono">
                      {step.timeOffset}
                    </span>
                  </div>

                  {step.safeguardType && (
                    <div className="pl-7">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/60">
                        {step.safeguardType}
                      </span>
                    </div>
                  )}

                  <p className="text-xs text-slate-300 font-sans pl-7">
                    {step.description}
                  </p>
                </div>

                {idx < scenario.interventionPath.length - 1 && (
                  <div className="flex justify-center my-1.5">
                    <ArrowDown className="w-4 h-4 text-cyan-600/70" />
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="p-3 rounded-lg bg-black/40 border border-cyan-900/40 text-[11px] font-mono text-emerald-300/90">
            Simulated Result: Controlled deceleration prevents extreme vibration peak, avoids mechanical seal rupture, and reduces recovery time.
          </div>
        </div>
      </div>

      {/* Recommended Engineering Safeguards & Barrier Analysis */}
      <div className="rounded-xl border border-slate-800 bg-[#0a0f1d] p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-xs font-bold uppercase tracking-wider text-white">
              Preventative Safeguards & Barrier Analysis
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            3 Engineering Defense Lines
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {scenario.safeguards.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 space-y-2.5 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {item.category}
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                      item.status === 'Recommended Intervention'
                        ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                        : 'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
                <h4 className="font-mono text-xs font-bold text-white">{item.title}</h4>
                <p className="text-xs text-slate-300 font-sans mt-2 leading-relaxed">
                  {item.recommendation}
                </p>
              </div>

              <div className="pt-2 border-t border-slate-800/60 text-[10px] font-mono text-slate-500">
                Actionable maintenance modification
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
