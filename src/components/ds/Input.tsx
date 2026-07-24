import React from 'react';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size' | 'prefix'> {
  size?: 'md' | 'sm';
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export function Input({ size = 'md', prefix, suffix, className, style, ...props }: InputProps) {
  const sizeClass = size === 'sm' ? 'astra-input-shell--sm' : undefined;
  const classes = ['astra-input-shell', sizeClass, className].filter(Boolean).join(' ');
  return (
    <div className={classes} style={style}>
      {prefix}
      <input {...props} />
      {suffix}
    </div>
  );
}
