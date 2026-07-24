import React from 'react';

export interface SlideOverProps {
  width?: number;
  title: React.ReactNode;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export function SlideOver({ width = 400, title, actions, children, className, style }: SlideOverProps) {
  return (
    <aside
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        width,
        height: '100%',
        minHeight: 0,
        background: 'var(--surface)',
        borderLeft: '1px solid var(--border-soft)',
        flexShrink: 0,
        ...style,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '12px 16px',
          minHeight: 56,
        }}
      >
        <span
          style={{
            font: 'var(--text-label-md)',
            letterSpacing: 'var(--tracking-label-md)',
            color: 'var(--text-strong)',
            flex: 1,
          }}
        >
          {title}
        </span>
        {actions ? <div style={{ marginLeft: 'auto' }}>{actions}</div> : null}
      </div>
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: '8px 20px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
        }}
      >
        {children}
      </div>
    </aside>
  );
}
