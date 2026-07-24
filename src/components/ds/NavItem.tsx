import React from 'react';

export interface NavItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: React.ReactNode;
  active?: boolean;
  className?: string;
}

export function NavItem({ icon, active = false, className, children, ...props }: NavItemProps) {
  const classes = ['astra-nav-item', active ? 'astra-nav-item--active' : undefined, className]
    .filter(Boolean)
    .join(' ');
  return (
    <button
      type="button"
      className={classes}
      aria-current={active ? 'page' : undefined}
      {...props}
    >
      {icon}
      <span style={{ textAlign: 'left', flex: 1 }}>{children}</span>
    </button>
  );
}
