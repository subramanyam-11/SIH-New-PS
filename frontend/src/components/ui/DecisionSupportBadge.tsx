'use client';

import React, { useState } from 'react';
import { Info, HelpCircle } from 'lucide-react';

interface DecisionSupportBadgeProps {
  className?: string;
  size?: 'xs' | 'sm' | 'md';
  customTooltip?: string;
}

export function DecisionSupportBadge({
  className = '',
  size = 'sm',
  customTooltip
}: DecisionSupportBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const tooltipText = customTooltip || 
    "Decision support only: Automation assists officers; statutory scrutiny, inspections, and final decisions stay with authorized humans.";

  const sizeClasses = {
    xs: "px-1.5 py-0.5 text-[10px] gap-1",
    sm: "px-2 py-0.5 text-[11px] gap-1",
    md: "px-2.5 py-1 text-xs gap-1.5",
  };

  const iconSizes = {
    xs: "w-2.5 h-2.5",
    sm: "w-3 h-3",
    md: "w-3.5 h-3.5",
  };

  return (
    <div className="relative inline-flex items-center">
      <span
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => setShowTooltip(!showTooltip)}
        className={`inline-flex items-center font-medium rounded-full cursor-help bg-amber-50 text-amber-900 border border-amber-200/80 shadow-xs hover:bg-amber-100 transition-colors ${sizeClasses[size]} ${className}`}
        role="status"
        aria-label="Decision support only"
      >
        <Info className={`${iconSizes[size]} text-amber-700 flex-shrink-0`} />
        <span className="font-semibold tracking-tight">Decision support only</span>
      </span>

      {showTooltip && (
        <div
          className="absolute z-50 bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-2 text-xs leading-relaxed text-slate-800 bg-white border border-slate-200 rounded-lg shadow-lg"
          role="tooltip"
        >
          <div className="flex items-start gap-1.5">
            <HelpCircle className="w-3.5 h-3.5 text-amber-600 mt-0.5 flex-shrink-0" />
            <p className="text-[11px]">{tooltipText}</p>
          </div>
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-white" />
        </div>
      )}
    </div>
  );
}
