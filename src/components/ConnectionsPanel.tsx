import { Button, SlideOver, StatusChip } from './ds';
import { ChipStatus } from './ds/StatusChip';
import { SOURCE_META, Source } from '../lib/data';

export type ConnectionKey = 'gmail' | 'outlook' | 'teams' | 'fireflies';
export type ConnectionStatus = 'connected' | 'checking' | 'disconnected';

export interface ConnectionState {
  enabled: boolean;
  status: ConnectionStatus;
}

export type ConnectionsState = Record<ConnectionKey, ConnectionState>;

export interface ConnectionsPanelProps {
  connections: ConnectionsState;
  rechecking: boolean;
  onToggle: (key: ConnectionKey) => void;
  onRecheckAll: () => void;
}

const CONNECTION_DEFS: { key: ConnectionKey; label: string; source: Source }[] = [
  { key: 'gmail', label: 'Gmail', source: 'Gmail' },
  { key: 'outlook', label: 'Outlook', source: 'Outlook' },
  { key: 'teams', label: 'Teams', source: 'Teams' },
  { key: 'fireflies', label: 'Fireflies', source: 'Fireflies' },
];

function chipStatusFor(status: ConnectionStatus): ChipStatus {
  if (status === 'connected') return 'active';
  if (status === 'checking') return 'pending';
  return 'blocked';
}

function statusLabelFor(status: ConnectionStatus): string {
  if (status === 'connected') return 'Connected';
  if (status === 'checking') return 'Checking';
  return 'Not connected';
}

export function ConnectionsPanel({ connections, rechecking, onToggle, onRecheckAll }: ConnectionsPanelProps) {
  return (
    <SlideOver
      title="Connections"
      actions={
        <Button variant="secondary" size="sm" onClick={onRecheckAll}>
          {rechecking ? 'Checking…' : 'Recheck All'}
        </Button>
      }
    >
      {CONNECTION_DEFS.map((def) => {
        const conn = connections[def.key];
        const meta = SOURCE_META[def.source];
        const toggleBg = conn.enabled ? 'var(--navy-800)' : 'var(--gray-200)';
        const knobLeft = conn.enabled ? '20px' : '2px';
        return (
          <div
            key={def.key}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: 12,
              borderRadius: 'var(--radius-10)',
              boxShadow: 'var(--shadow-ring-soft)',
            }}
          >
            <span
              style={{
                width: 36,
                height: 36,
                borderRadius: 'var(--radius-full)',
                background: meta.bg,
                color: meta.color,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                font: 'var(--text-label-sm)',
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              {meta.initial}
            </span>
            <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ font: 'var(--text-label-sm)', color: 'var(--text-strong)' }}>{def.label}</span>
              <StatusChip status={chipStatusFor(conn.status)}>{statusLabelFor(conn.status)}</StatusChip>
            </div>
            <button
              type="button"
              onClick={() => onToggle(def.key)}
              aria-pressed={conn.enabled}
              style={{
                width: 44,
                height: 26,
                borderRadius: 'var(--radius-full)',
                border: 'none',
                cursor: 'pointer',
                background: toggleBg,
                position: 'relative',
                transition: 'background var(--duration-default) var(--ease-out)',
                flexShrink: 0,
              }}
            >
              <span
                style={{
                  position: 'absolute',
                  top: 2,
                  left: knobLeft,
                  width: 22,
                  height: 22,
                  borderRadius: '50%',
                  background: '#fff',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.25)',
                  transition: 'left 220ms cubic-bezier(0.34,1.2,0.64,1)',
                }}
              />
            </button>
          </div>
        );
      })}
    </SlideOver>
  );
}
