import React from 'react';

export interface KPICardProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export function KPICard({ label, value, className, style, ...props }: KPICardProps) {
  const classes = ['astra-card', 'astra-card--ring', className].filter(Boolean).join(' ');
  return (
    <div
      className={classes}
      style={{ display: 'flex', flexDirection: 'column', gap: 4, ...style }}
      {...props}
    >
      <span
        style={{
          font: 'var(--text-label-sm)',
          letterSpacing: 'var(--tracking-label-sm)',
          color: 'var(--gray-600)',
        }}
      >
        {label}
      </span>
      <div
        style={{
          font: 'var(--text-title-h4)',
          letterSpacing: 'var(--tracking-h4)',
          color: 'var(--text-strong)',
        }}
      >
        {value}
      </div>
    </div>
  );
}
