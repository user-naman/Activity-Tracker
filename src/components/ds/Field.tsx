import React from 'react';

export interface FieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: React.ReactNode;
  required?: boolean;
  helper?: React.ReactNode;
  helperTone?: 'default' | 'error';
  children: React.ReactNode;
}

export function Field({ label, required, helper, helperTone = 'default', children, style, ...props }: FieldProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, ...style }} {...props}>
      {label ? (
        <label className="astra-field-label">
          {label} {required && <em>*</em>}
        </label>
      ) : null}
      {children}
      {helper ? (
        <span
          style={{
            font: 'var(--text-paragraph-xs)',
            color: helperTone === 'error' ? 'var(--red-600)' : 'var(--slate-500)',
          }}
        >
          {helper}
        </span>
      ) : null}
    </div>
  );
}
