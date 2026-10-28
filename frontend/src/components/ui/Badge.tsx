import React from 'react';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'secondary' | 'destructive' | 'default' | 'outline';
  size?: 'sm' | 'md';
  children: React.ReactNode;
}

export function Badge({
  variant = 'neutral',
  size = 'md',
  className = '',
  children,
  ...props
}: BadgeProps) {
  const baseStyles = "inline-flex items-center font-medium rounded-full";
  
  const sizeStyles = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-0.5 text-xs tracking-wide",
  };

  const variantStyles = {
    neutral: "bg-slate-100 text-slate-700 border border-slate-200",
    secondary: "bg-slate-100 text-slate-700 border border-slate-200",
    default: "bg-blue-900 text-white",
    info: "bg-blue-50 text-blue-700 border border-blue-200",
    success: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    warning: "bg-amber-50 text-amber-800 border border-amber-200",
    danger: "bg-rose-50 text-rose-700 border border-rose-200",
    destructive: "bg-rose-100 text-rose-800 border border-rose-300",
    outline: "border border-slate-300 text-slate-700 bg-transparent",
  };

  return (
    <span
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
