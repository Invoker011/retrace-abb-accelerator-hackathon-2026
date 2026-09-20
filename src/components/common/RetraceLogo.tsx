import React from 'react';

interface RetraceLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showSubtitle?: boolean;
  showTagline?: boolean;
  className?: string;
}

/**
 * RETRACE Branding Component
 * Renders technical uppercase RETRACE text where 'A' is highlighted in industrial red (#FF1A1A).
 * Follows industrial forensic software aesthetic without gradients or playful styling.
 */
export const RetraceLogo: React.FC<RetraceLogoProps> = ({
  size = 'md',
  showSubtitle = true,
  showTagline = false,
  className = '',
}) => {
  const sizeStyles = {
    sm: {
      text: 'text-base tracking-wider',
      subtitle: 'text-[10px]',
      tagline: 'text-[10px]',
    },
    md: {
      text: 'text-xl tracking-wider',
      subtitle: 'text-[11px]',
      tagline: 'text-[11px]',
    },
    lg: {
      text: 'text-2xl tracking-wider',
      subtitle: 'text-xs',
      tagline: 'text-xs',
    },
  };

  const currentSize = sizeStyles[size];

  return (
    <div className={`flex flex-col select-none ${className}`}>
      {/* Brand Title: RETRACE with bright industrial red 'A' */}
      <div className="flex items-center gap-1.5 leading-none">
        <span
          className={`font-mono font-bold text-white uppercase inline-flex items-baseline ${currentSize.text}`}
          aria-label="RETRACE"
        >
          <span>RETR</span>
          <span className="text-[#FF1A1A] font-extrabold">A</span>
          <span>CE</span>
        </span>
      </div>

      {/* Subtitle: Industrial Incident Forensics */}
      {showSubtitle && (
        <span
          className={`font-mono font-medium text-slate-300/90 tracking-wide uppercase mt-1 leading-tight ${currentSize.subtitle}`}
        >
          Industrial Incident Forensics
        </span>
      )}

      {/* Tagline: Reconstruct. Replay. Learn. */}
      {showTagline && (
        <span
          className={`font-mono font-medium text-cyan-400/90 tracking-wide mt-0.5 leading-tight ${currentSize.tagline}`}
        >
          Reconstruct. Replay. Learn.
        </span>
      )}
    </div>
  );
};
