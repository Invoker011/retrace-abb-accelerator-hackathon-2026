import React from 'react';
import { EvidenceCategory } from '../../types';
import {
  Activity,
  Cpu,
  Database,
  FileText,
  Wrench,
  Camera,
} from 'lucide-react';

interface EvidenceBadgeProps {
  category?: EvidenceCategory | string;
  size?: 'sm' | 'md';
  onClick?: () => void;
  className?: string;
}

export const EvidenceBadge: React.FC<EvidenceBadgeProps> = ({
  category,
  size = 'md',
  onClick,
  className = '',
}) => {
  const getCategoryConfig = () => {
    const cat = (category || '').toLowerCase().trim();

    if (cat.includes('plc') || cat.includes('scada')) {
      return {
        label: 'PLC / SCADA',
        icon: <Cpu className="w-3.5 h-3.5 text-cyan-400" />,
        color: 'text-cyan-400 bg-cyan-950/40 border-cyan-800/40 hover:border-cyan-600/60',
      };
    }
    if (cat.includes('vfd') || cat.includes('drive')) {
      return {
        label: 'VFD / Drive Logs',
        icon: <Activity className="w-3.5 h-3.5 text-blue-400" />,
        color: 'text-blue-400 bg-blue-950/40 border-blue-800/40 hover:border-blue-600/60',
      };
    }
    if (
      cat.includes('historian') ||
      cat.includes('time-series') ||
      cat.includes('telemetry') ||
      cat.includes('sensor')
    ) {
      return {
        label: 'Historian Data',
        icon: <Database className="w-3.5 h-3.5 text-emerald-400" />,
        color: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40 hover:border-emerald-600/60',
      };
    }
    if (
      cat.includes('engineering') ||
      cat.includes('doc') ||
      cat.includes('manual') ||
      cat.includes('p&id') ||
      cat.includes('drawing')
    ) {
      return {
        label: 'Engineering Documents',
        icon: <FileText className="w-3.5 h-3.5 text-purple-400" />,
        color: 'text-purple-400 bg-purple-950/40 border-purple-800/40 hover:border-purple-600/60',
      };
    }
    if (
      cat.includes('maintenance') ||
      cat.includes('inspection') ||
      cat.includes('work_order') ||
      cat.includes('repair')
    ) {
      return {
        label: 'Maintenance / Inspection Records',
        icon: <Wrench className="w-3.5 h-3.5 text-amber-400" />,
        color: 'text-amber-400 bg-amber-950/40 border-amber-800/40 hover:border-amber-600/60',
      };
    }
    if (
      cat.includes('tech') ||
      cat.includes('note') ||
      cat.includes('photo') ||
      cat.includes('report') ||
      cat.includes('observation')
    ) {
      return {
        label: 'Technician Notes & Photos',
        icon: <Camera className="w-3.5 h-3.5 text-rose-400" />,
        color: 'text-rose-400 bg-rose-950/40 border-rose-800/40 hover:border-rose-600/60',
      };
    }

    return {
      label: category || 'Industrial Evidence',
      icon: <FileText className="w-3.5 h-3.5 text-slate-400" />,
      color: 'text-slate-300 bg-slate-800/40 border-slate-700/50 hover:border-slate-500/60',
    };
  };

  const config = getCategoryConfig();
  const sizeClasses = size === 'sm' ? 'text-[10px] px-2 py-0.5 gap-1' : 'text-xs px-2.5 py-1 gap-1.5';

  return (
    <span
      onClick={onClick}
      className={`inline-flex items-center rounded border font-mono font-medium transition-all ${
        onClick ? 'cursor-pointer hover:scale-105' : ''
      } ${config.color} ${sizeClasses} ${className}`}
    >
      {config.icon}
      <span>{category || config.label}</span>
    </span>
  );
};
