import React, { useRef, useState } from 'react';
import { Badge, CountBadge, EmptyState } from './ds';
import { RadarCard } from './RadarCard';
import { PRIORITY_META, RadarItem, SOURCE_META, STATUS_META, Status, rankItems } from '../lib/data';

export interface KanbanBoardProps {
  items: RadarItem[];
  onItemsChange: (updater: (items: RadarItem[]) => RadarItem[]) => void;
  pulseCol: Status | null;
  onEditItem: (item: RadarItem) => void;
}

const COLUMN_KEYS: Status[] = ['todo', 'inProgress', 'done'];

const COLUMN_EMPTY_LABEL: Record<Status, string> = {
  todo: 'Inbox zero',
  inProgress: 'All clear',
  done: 'Nothing done yet',
};

const COLUMN_EMPTY_CAPTION: Record<Status, string> = {
  todo: 'Nothing new to file this morning.',
  inProgress: 'Nothing in progress right now.',
  done: 'Nothing marked done yet today.',
};

const STATUS_ORDER: Status[] = ['todo', 'inProgress', 'done'];

interface GrabPoint {
  x: number;
  y: number;
}

export function KanbanBoard({ items, onItemsChange, pulseCol, onEditItem }: KanbanBoardProps) {
  const [dragId, setDragId] = useState<number | null>(null);
  const [hoverCol, setHoverCol] = useState<Status | null>(null);
  const [dragX, setDragX] = useState(0);
  const [dragY, setDragY] = useState(0);

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const grabOffset = useRef<GrabPoint>({ x: 0, y: 0 });
  const startPoint = useRef<GrabPoint>({ x: 0, y: 0 });

  const handlePointerDown = (item: RadarItem, colKey: Status, e: React.PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    const rect = e.currentTarget.getBoundingClientRect();
    grabOffset.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    startPoint.current = { x: e.clientX, y: e.clientY };
    setDragId(item.id);
    setHoverCol(colKey);
    setDragX(e.clientX);
    setDragY(e.clientY);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (dragId === null) return;
    let hover = hoverCol;
    const el = document.elementFromPoint(e.clientX, e.clientY);
    const colEl = el && el.closest ? (el.closest('[data-kcol]') as HTMLElement | null) : null;
    if (colEl) hover = colEl.getAttribute('data-kcol') as Status;
    setDragX(e.clientX);
    setDragY(e.clientY);
    setHoverCol(hover);
  };

  const handlePointerUp = () => {
    if (dragId === null) return;
    const targetCol = hoverCol;
    const moved = Math.hypot(dragX - startPoint.current.x, dragY - startPoint.current.y);

    onItemsChange((prev) =>
      prev.map((i) => {
        if (i.id !== dragId) return i;
        if (moved < 6) {
          const idx = STATUS_ORDER.indexOf(i.status);
          const next = STATUS_ORDER[(idx + 1) % STATUS_ORDER.length];
          return { ...i, status: next, carried: next === 'todo' ? true : i.carried };
        }
        if (!targetCol || targetCol === i.status) return i;
        const carried = targetCol === 'todo';
        return { ...i, status: targetCol, carried: carried ? true : i.carried };
      }),
    );

    setDragId(null);
    setHoverCol(null);
  };

  const draggedItem = dragId !== null ? items.find((i) => i.id === dragId) ?? null : null;

  let floatLeft = 0;
  let floatTop = 0;
  if (draggedItem && wrapRef.current) {
    const wr = wrapRef.current.getBoundingClientRect();
    floatLeft = dragX - wr.left - grabOffset.current.x;
    floatTop = dragY - wr.top - grabOffset.current.y;
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative', flex: 1, display: 'flex', gap: 16, minHeight: 0 }}>
      {COLUMN_KEYS.map((colKey) => {
        const colItems = rankItems(items.filter((i) => i.status === colKey));
        const isHover = dragId !== null && hoverCol === colKey;
        const isPulsing = pulseCol === colKey;
        const bg = isHover ? 'var(--brand-50)' : 'var(--bg-page-tint)';
        const ringStyle = isHover
          ? 'inset 0 0 0 2px var(--brand-300)'
          : isPulsing
            ? 'inset 0 0 0 2px var(--brand-500)'
            : 'none';

        return (
          <div
            key={colKey}
            data-kcol={colKey}
            style={{
              flex: 1,
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
              background: bg,
              borderRadius: 'var(--radius-xl)',
              padding: 12,
              gap: 10,
              boxShadow: ringStyle,
              transition: 'background 150ms var(--ease-out), box-shadow 150ms var(--ease-out)',
              minHeight: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 4px', flexShrink: 0 }}>
              <span
                style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_META[colKey].dot }}
              />
              <span
                style={{
                  font: 'var(--text-label-sm)',
                  letterSpacing: 'var(--tracking-label-sm)',
                  color: 'var(--text-strong)',
                }}
              >
                {STATUS_META[colKey].label}
              </span>
              <CountBadge>{colItems.length}</CountBadge>
            </div>
            <div
              style={{
                flex: 1,
                minHeight: 0,
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                paddingBottom: 4,
              }}
            >
              {colItems.length === 0 ? (
                <EmptyState title={COLUMN_EMPTY_LABEL[colKey]} caption={COLUMN_EMPTY_CAPTION[colKey]} />
              ) : (
                colItems.map((item) => (
                  <RadarCard
                    key={item.id}
                    item={item}
                    opacity={item.id === dragId ? 0.35 : 1}
                    onPointerDown={(e) => handlePointerDown(item, colKey, e)}
                    onPointerMove={handlePointerMove}
                    onPointerUp={handlePointerUp}
                    onEdit={onEditItem}
                  />
                ))
              )}
            </div>
          </div>
        );
      })}

      {draggedItem ? (
        <div
          style={{
            position: 'absolute',
            left: floatLeft,
            top: floatTop,
            width: 280,
            zIndex: 100,
            pointerEvents: 'none',
            transform: 'rotate(-1.5deg) scale(1.03)',
            background: 'var(--surface)',
            borderRadius: 'var(--radius-10)',
            boxShadow: '0 20px 32px rgba(19,28,40,0.28)',
            padding: 12,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
              <span
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: '50%',
                  background: SOURCE_META[draggedItem.source].bg,
                  color: SOURCE_META[draggedItem.source].color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  font: 'var(--text-label-xs)',
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                {SOURCE_META[draggedItem.source].initial}
              </span>
              <span style={{ font: 'var(--text-label-sm)', color: 'var(--text-strong)' }}>
                {draggedItem.sender}
              </span>
            </div>
            <Badge tone={PRIORITY_META[draggedItem.priority].tone}>{draggedItem.priority}</Badge>
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
            {draggedItem.subject}
          </span>
        </div>
      ) : null}
    </div>
  );
}
