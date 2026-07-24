import React from 'react';

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  size?: 'md' | 'sm';
  className?: string;
  style?: React.CSSProperties;
}

function ChevronDownIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      style={{ pointerEvents: 'none', marginLeft: -20, flexShrink: 0 }}
    >
      <path
        d="m6 9 6 6 6-6"
        stroke="var(--slate-500)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Select({ size = 'md', className, style, children, ...props }: SelectProps) {
  const sizeClass = size === 'sm' ? 'astra-input-shell--sm' : undefined;
  const classes = ['astra-input-shell', sizeClass, className].filter(Boolean).join(' ');
  return (
    <div className={classes} style={{ paddingRight: 8, ...style }}>
      <select style={{ cursor: 'pointer', appearance: 'none', WebkitAppearance: 'none' }} {...props}>
        {children}
      </select>
      <ChevronDownIcon />
    </div>
  );
}
