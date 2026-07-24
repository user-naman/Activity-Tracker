import React from 'react';
import { Badge } from './ds';
import { PRIORITY_META, SOURCE_META, RadarItem } from '../lib/data';

export interface RadarCardProps {
  item: RadarItem;
  opacity?: number;
  onPointerDown?: (e: React.PointerEvent<HTMLDivElement>) => void;
  onPointerMove?: (e: React.PointerEvent<HTMLDivElement>) => void;
  onPointerUp?: (e: React.PointerEvent<HTMLDivElement>) => void;
  onEdit?: (item: RadarItem) => void;
  style?: React.CSSProperties;
}

function PencilIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 20h9"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function TriangleAlertIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      style={{ flexShrink: 0, marginTop: 2 }}
    >
      <path
        d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
        stroke="var(--red-500)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <line x1="12" y1="9" x2="12" y2="13" stroke="var(--red-500)" strokeWidth="2" strokeLinecap="round" />
      <line x1="12" y1="17" x2="12.01" y2="17" stroke="var(--red-500)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function RadarCard({ item, opacity = 1, onPointerDown, onPointerMove, onPointerUp, onEdit, style }: RadarCardProps) {
  const sourceMeta = SOURCE_META[item.source];
  const priorityMeta = PRIORITY_META[item.priority];

  return (
    <div
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      style={{
        background: 'var(--surface)',
        borderRadius: 'var(--radius-10)',
        boxShadow: 'var(--shadow-control)',
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        cursor: 'grab',
        touchAction: 'none',
        opacity,
        transition: 'opacity 150ms var(--ease-out)',
        ...style,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <span
            style={{
              width: 26,
              height: 26,
              borderRadius: '50%',
              background: sourceMeta.bg,
              color: sourceMeta.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              font: 'var(--text-label-xs)',
              fontWeight: 700,
              flexShrink: 0,
            }}
          >
            {sourceMeta.initial}
          </span>
          <span
            style={{
              font: 'var(--text-label-sm)',
              letterSpacing: 'var(--tracking-label-sm)',
              color: 'var(--text-strong)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {item.sender}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
          <Badge tone={priorityMeta.tone}>{item.priority}</Badge>
          <button
            type="button"
            aria-label="Edit item"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              onEdit?.(item);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 20,
              height: 20,
              border: 'none',
              background: 'transparent',
              boxShadow: 'none',
              cursor: 'pointer',
              padding: 0,
              color: 'var(--slate-500)',
              transition: 'color var(--duration-default) var(--ease-out)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-strong)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--slate-500)')}
          >
            <PencilIcon />
          </button>
        </div>
      </div>
      <span
        style={{
          font: 'var(--text-paragraph-xs)',
          color: 'var(--slate-500)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {item.subject}
      </span>
      {item.priority === 'P1' && item.reason ? (
        <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
          <TriangleAlertIcon />
          <span
            style={{
              font: 'var(--text-paragraph-xs)',
              color: 'var(--red-700)',
              whiteSpace: 'normal',
            }}
          >
            {item.reason}
          </span>
        </div>
      ) : null}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ font: 'var(--text-paragraph-xs)', color: 'var(--slate-400)' }}>{item.time}</span>
        {item.carried ? (
          <span style={{ font: 'var(--text-paragraph-xs)', color: 'var(--orange-600)' }}>Carried</span>
        ) : null}
      </div>
    </div>
  );
}
