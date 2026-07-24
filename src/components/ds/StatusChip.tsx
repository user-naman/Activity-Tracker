import React from 'react';

export type ChipStatus = 'active' | 'inProgress' | 'blocked' | 'pending' | 'activeRequest' | 'draft';

export interface StatusChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  status?: ChipStatus;
  onDark?: boolean;
  icon?: React.ReactNode;
  className?: string;
}

const DOT_COLORS: Record<ChipStatus, string> = {
  active: 'var(--green-500)',
  activeRequest: 'var(--orange-500)',
  inProgress: 'var(--blue-500)',
  blocked: 'var(--red-500)',
  pending: 'var(--yellow-500)',
  draft: 'var(--gray-400)',
};

export function StatusChip({
  status = 'active',
  onDark = false,
  icon,
  className,
  children,
  ...props
}: StatusChipProps) {
  const classes = ['astra-chip', onDark ? 'astra-chip--on-dark' : undefined, className]
    .filter(Boolean)
    .join(' ');
  return (
    <span className={classes} {...props}>
      {icon ?? <span className="astra-dot" style={{ background: DOT_COLORS[status] }} />}
      {children}
    </span>
  );
}
