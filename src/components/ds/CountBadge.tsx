import React from 'react';

export interface CountBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  className?: string;
}

export function CountBadge({ className, children, ...props }: CountBadgeProps) {
  const classes = ['astra-pill', 'astra-pill--count', className].filter(Boolean).join(' ');
  return (
    <span className={classes} {...props}>
      {children}
    </span>
  );
}
