import React from 'react';

export interface EmptyStateProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  icon?: React.ReactNode;
  title: React.ReactNode;
  caption?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, caption, action, className, ...props }: EmptyStateProps) {
  return (
    <div
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        background: 'var(--surface)',
        borderRadius: 'var(--radius-xl)',
        boxShadow: 'var(--shadow-ring-soft)',
        padding: '40px 32px',
        textAlign: 'center',
      }}
      {...props}
    >
      {icon}
      <div
        style={{
          font: 'var(--text-label-sm)',
          letterSpacing: 'var(--tracking-label-sm)',
          color: 'var(--text-strong)',
        }}
      >
        {title}
      </div>
      {caption ? (
        <div style={{ font: 'var(--text-paragraph-xs)', color: 'var(--slate-500)' }}>{caption}</div>
      ) : null}
      {action}
    </div>
  );
}
