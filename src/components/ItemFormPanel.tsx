import React, { useState } from 'react';
import { Button, Field, Input, Select, SlideOver } from './ds';
import { Priority, SOURCE_META, Source, STATUS_META, Status } from '../lib/data';

export interface ItemFormValues {
  priority: Priority;
  source: Source;
  sender: string;
  subject: string;
  time: string;
  status: Status;
  reason: string; // may be empty; only persisted/shown when priority is P1
  carried: boolean;
}

export interface ItemFormPanelProps {
  mode: 'create' | 'edit';
  initialValues: ItemFormValues;
  onSave: (values: ItemFormValues) => void;
  onCancel: () => void;
  onDelete?: () => void; // present only in edit mode
}

const PRIORITY_OPTIONS: Priority[] = ['P1', 'P2', 'P3'];
const SOURCE_OPTIONS = Object.keys(SOURCE_META) as Source[];
const STATUS_OPTIONS: Status[] = ['todo', 'inProgress', 'done'];

const TIME_PATTERN = /^\d{1,2}:\d{2}\s*(AM|PM)$/i;

interface FormErrors {
  sender?: string;
  subject?: string;
  time?: string;
  reason?: string;
}

export function ItemFormPanel({ mode, initialValues, onSave, onCancel, onDelete }: ItemFormPanelProps) {
  const [values, setValues] = useState<ItemFormValues>(initialValues);
  const [errors, setErrors] = useState<FormErrors>({});

  const update = <K extends keyof ItemFormValues>(key: K, value: ItemFormValues[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const nextErrors: FormErrors = {};
    if (!values.sender.trim()) nextErrors.sender = 'Sender is required.';
    if (!values.subject.trim()) nextErrors.subject = 'Subject is required.';
    if (!TIME_PATTERN.test(values.time.trim())) nextErrors.time = 'Use a time like 9:30 AM.';
    if (values.priority === 'P1' && !values.reason.trim()) nextErrors.reason = "Required when priority is P1";

    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      return;
    }
    setErrors({});
    onSave(values);
  };

  return (
    <SlideOver title={mode === 'create' ? 'New Item' : 'Edit Item'}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, flex: 1, minHeight: 0 }}>
          <Field label="Priority">
            <Select value={values.priority} onChange={(e) => update('priority', e.target.value as Priority)}>
              {PRIORITY_OPTIONS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Source">
            <Select value={values.source} onChange={(e) => update('source', e.target.value as Source)}>
              {SOURCE_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Sender" required helper={errors.sender} helperTone="error">
            <Input
              value={values.sender}
              onChange={(e) => update('sender', e.target.value)}
              placeholder="e.g. Geetika Chanana"
            />
          </Field>

          <Field label="Subject" required helper={errors.subject} helperTone="error">
            <Input
              value={values.subject}
              onChange={(e) => update('subject', e.target.value)}
              placeholder="One-line summary shown on the card"
            />
          </Field>

          <Field label="Time" required helper={errors.time} helperTone="error">
            <Input
              value={values.time}
              onChange={(e) => update('time', e.target.value)}
              placeholder="e.g. 9:30 AM"
            />
          </Field>

          <Field label="Status">
            <Select value={values.status} onChange={(e) => update('status', e.target.value as Status)}>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {STATUS_META[s].label}
                </option>
              ))}
            </Select>
          </Field>

          {values.priority === 'P1' ? (
            <Field label="Why it's a P1" helper={errors.reason ?? 'Required when priority is P1'} helperTone={errors.reason ? 'error' : 'default'}>
              <div className="astra-input-shell" style={{ height: 'auto', alignItems: 'flex-start', padding: '8px 12px' }}>
                <textarea
                  rows={2}
                  style={{ resize: 'vertical' }}
                  value={values.reason}
                  onChange={(e) => update('reason', e.target.value)}
                />
              </div>
            </Field>
          ) : null}

          <label style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              type="button"
              onClick={() => update('carried', !values.carried)}
              aria-pressed={values.carried}
              style={{
                width: 44,
                height: 26,
                borderRadius: 'var(--radius-full)',
                border: 'none',
                cursor: 'pointer',
                background: values.carried ? 'var(--navy-800)' : 'var(--gray-200)',
                position: 'relative',
                transition: 'background var(--duration-default) var(--ease-out)',
                flexShrink: 0,
              }}
            >
              <span
                style={{
                  position: 'absolute',
                  top: 2,
                  left: values.carried ? '20px' : '2px',
                  width: 22,
                  height: 22,
                  borderRadius: '50%',
                  background: '#fff',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.25)',
                  transition: 'left 220ms cubic-bezier(0.34,1.2,0.64,1)',
                }}
              />
            </button>
            <span style={{ font: 'var(--text-label-sm)', color: 'var(--text-strong)' }}>
              Carried over from a previous day
            </span>
          </label>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            paddingTop: 12,
            borderTop: '1px solid var(--border-soft)',
            flexShrink: 0,
          }}
        >
          <div>
            {mode === 'edit' && onDelete ? (
              <Button type="button" variant="ghost" style={{ color: 'var(--red-600)' }} onClick={onDelete}>
                Delete
              </Button>
            ) : null}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save
            </Button>
          </div>
        </div>
      </form>
    </SlideOver>
  );
}
