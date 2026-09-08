import React from 'react';
import { FindingCategory } from '../../types';
import { CheckCircle2, GitCompare, HelpCircle, Lightbulb } from 'lucide-react';

interface FindingBadgeProps {
  category: FindingCategory;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const FindingBadge: React.FC<FindingBadgeProps> = ({
  category,
  showIcon = true,
  size = 'md',
  className = '',
}) => {
  const getBadgeConfig = () => {
    switch (category) {
      case 'OBSERVED':
        return {
          label: 'OBSERVED',
          desc: 'Directly supported by operational telemetry or hardware logs',
          bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/20',
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />,
          dot: 'bg-cyan-400',
        };
      case 'CORRELATED':
        return {
          label: 'CORRELATED',
          desc: 'Relationship supported by timing & topology, not proven causal',
          bg: 'bg-blue-500/10 text-blue-400 border-blue-500/30 hover:bg-blue-500/20',
          icon: <GitCompare className="w-3.5 h-3.5 text-blue-400" />,
          dot: 'bg-blue-400',
        };
      case 'HYPOTHESIS':
        return {
          label: 'HYPOTHESIS',
          desc: 'Plausible explanation requiring physical or teardown confirmation',
          bg: 'bg-purple-500/10 text-purple-400 border-purple-500/30 hover:bg-purple-500/20',
          icon: <Lightbulb className="w-3.5 h-3.5 text-purple-400" />,
          dot: 'bg-purple-400',
        };
      case 'UNKNOWN':
        return {
          label: 'UNKNOWN',
          desc: 'Insufficient evidence to determine from currently available sources',
          bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20',
          icon: <HelpCircle className="w-3.5 h-3.5 text-amber-400" />,
          dot: 'bg-amber-400',
        };
    }
  };

  const config = getBadgeConfig();

  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5 gap-1 tracking-wider',
    md: 'text-xs px-2.5 py-1 gap-1.5 tracking-wider font-semibold',
    lg: 'text-sm px-3.5 py-1.5 gap-2 tracking-wider font-bold',
  }[size];

  return (
    <span
      id={`finding-badge-${category.toLowerCase()}`}
      title={config.desc}
      className={`inline-flex items-center rounded-md border font-mono uppercase transition-colors select-none ${config.bg} ${sizeClasses} ${className}`}
    >
      {showIcon && config.icon}
      <span>{config.label}</span>
    </span>
  );
};
