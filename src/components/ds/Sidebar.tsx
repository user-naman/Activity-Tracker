import React from 'react';

export interface SidebarProps {
  header?: React.ReactNode;
  footer?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export function Sidebar({ header, footer, children, className, style }: SidebarProps) {
  const classes = ['astra-scroll', className].filter(Boolean).join(' ');
  return (
    <aside
      className={classes}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--navy-800)',
        width: 'var(--w-sidebar)',
        flexShrink: 0,
        ...style,
      }}
    >
      {header ? <div style={{ padding: '20px 16px' }}>{header}</div> : null}
      <nav style={{ flex: 1, overflowY: 'auto', padding: '0 12px' }}>{children}</nav>
      {footer}
    </aside>
  );
}
