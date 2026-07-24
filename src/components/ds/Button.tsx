import React from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'ai';
export type ButtonSize = 'md' | 'sm';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
  className?: string;
}

export function Button({
  variant = 'primary',
  size = 'md',
  iconLeft,
  iconRight,
  className,
  children,
  ...props
}: ButtonProps) {
  const sizeClass = size === 'sm' ? 'astra-btn--sm' : 'astra-btn--md';
  const classes = ['astra-btn', `astra-btn--${variant}`, sizeClass, className]
    .filter(Boolean)
    .join(' ');
  return (
    <button type="button" className={classes} {...props}>
      {iconLeft}
      {children}
      {iconRight}
    </button>
  );
}
