import React from 'react';

export type BadgeTone = 'danger' | 'warning' | 'info' | 'success' | 'neutral';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  onDark?: boolean;
  className?: string;
}

export function Badge({ tone = 'neutral', onDark = false, className, children, ...props }: BadgeProps) {
  const variant = onDark ? `astra-pill--on-dark-${tone}` : `astra-pill--${tone}`;
  const classes = ['astra-pill', variant, className].filter(Boolean).join(' ');
  return (
    <span className={classes} {...props}>
      {children}
    </span>
  );
}
