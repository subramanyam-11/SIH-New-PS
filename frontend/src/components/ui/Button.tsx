import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  disabled,
  children,
  ...props
}: ButtonProps) {
  const baseStyles = "inline-flex items-center justify-center font-medium transition-colors rounded border focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed";
  
  const sizeStyles = {
    sm: "px-2.5 py-1 text-xs",
    md: "px-3.5 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  };

  const variantStyles = {
    primary: "bg-[#0f2b5c] text-white border-transparent hover:bg-[#1e3a8a] focus:ring-[#0f2b5c]",
    secondary: "bg-slate-100 text-slate-800 border-slate-200 hover:bg-slate-200 focus:ring-slate-400",
    outline: "bg-transparent text-slate-700 border-slate-300 hover:bg-slate-50 focus:ring-slate-400",
    danger: "bg-red-600 text-white border-transparent hover:bg-red-700 focus:ring-red-500",
    ghost: "bg-transparent text-slate-600 border-transparent hover:bg-slate-100 focus:ring-slate-300",
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
