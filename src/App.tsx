import { useEffect, useRef, useState } from 'react';
import { Button, KPICard, NavItem, SegmentedControl, Sidebar, StatusChip } from './components/ds';
import { KanbanBoard } from './components/KanbanBoard';
import { ConnectionsPanel, ConnectionKey, ConnectionsState } from './components/ConnectionsPanel';
import { ItemFormPanel, ItemFormValues } from './components/ItemFormPanel';
import { RadarItem, Status, countStatuses, nextId } from './lib/data';
import { buildConnectorItems } from './lib/connectors';

type Mode = 'morning' | 'evening';

const NAV_ITEMS = ['Home', 'Daily Radar', 'Requests', 'Sourcing', 'Renewals', 'Settings'];

const MODE_OPTIONS = [
  { id: 'morning', label: 'Morning' },
  { id: 'evening', label: 'Evening' },
];

const INITIAL_CONNECTIONS: ConnectionsState = {
  gmail: { enabled: false, status: 'disconnected' },
  outlook: { enabled: true, status: 'connected' },
  teams: { enabled: false, status: 'disconnected' },
  fireflies: { enabled: false, status: 'disconnected' },
  slack: { enabled: true, status: 'connected' },
};

const EMPTY_FORM_VALUES: ItemFormValues = {
  priority: 'P2',
  source: 'Outlook',
  sender: '',
  subject: '',
  time: '',
  status: 'todo',
  reason: '',
  carried: false,
};

function pluralize(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

function CheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path
        d="M5 12l5 5 9-9"
        stroke="var(--green-600)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function App() {
  const [items, setItems] = useState<RadarItem[]>(() => buildConnectorItems());
  const [connections, setConnections] = useState<ConnectionsState>(INITIAL_CONNECTIONS);
  const [rechecking, setRechecking] = useState(false);
  const [mode, setMode] = useState<Mode>('morning');
  const [activePanel, setActivePanel] = useState<'connections' | 'itemForm' | null>(null);
  const [editingItem, setEditingItem] = useState<RadarItem | null>(null);
  const [pulseCol, setPulseCol] = useState<Status | null>(null);

  const pulseTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const recheckTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const connTimers = useRef<Partial<Record<ConnectionKey, ReturnType<typeof setTimeout>>>>({});

  useEffect(() => {
    return () => {
      clearTimeout(pulseTimer.current);
      clearTimeout(recheckTimer.current);
      Object.values(connTimers.current).forEach((t) => clearTimeout(t));
    };
  }, []);

  const handleItemsChange = (updater: (items: RadarItem[]) => RadarItem[]) => {
    setItems((prev) => updater(prev));
  };

  const pulseFolder = (col: Status) => {
    setPulseCol(col);
    clearTimeout(pulseTimer.current);
    pulseTimer.current = setTimeout(() => setPulseCol(null), 900);
  };

  const toggleConnection = (key: ConnectionKey) => {
    setConnections((prev) => {
      const cur = prev[key];
      const turningOn = !cur.enabled;
      return {
        ...prev,
        [key]: { enabled: turningOn, status: turningOn ? 'checking' : 'disconnected' },
      };
    });

    clearTimeout(connTimers.current[key]);
    const cur = connections[key];
    const turningOn = !cur.enabled;
    if (turningOn) {
      connTimers.current[key] = setTimeout(() => {
        setConnections((prev) => ({
          ...prev,
          [key]: { ...prev[key], status: 'connected' },
        }));
      }, 700);
    }
  };

  const recheckAll = () => {
    setConnections((prev) => {
      const next = { ...prev };
      (Object.keys(next) as ConnectionKey[]).forEach((k) => {
        next[k] = { ...next[k], status: next[k].enabled ? 'checking' : 'disconnected' };
      });
      return next;
    });
    setRechecking(true);

    clearTimeout(recheckTimer.current);
    recheckTimer.current = setTimeout(() => {
      setConnections((prev) => {
        const next = { ...prev };
        (Object.keys(next) as ConnectionKey[]).forEach((k) => {
          next[k] = { ...next[k], status: next[k].enabled ? 'connected' : 'disconnected' };
        });
        return next;
      });
      setRechecking(false);
    }, 900);
  };

  const openCreateForm = () => {
    setEditingItem(null);
    setActivePanel('itemForm');
  };

  const openEditForm = (item: RadarItem) => {
    setEditingItem(item);
    setActivePanel('itemForm');
  };

  const closeForm = () => {
    setActivePanel(null);
    setEditingItem(null);
  };

  const saveItem = (values: ItemFormValues) => {
    const reason = values.priority === 'P1' ? values.reason || undefined : undefined;

    if (editingItem) {
      const id = editingItem.id;
      setItems((prev) =>
        prev.map((i) => (i.id === id ? { ...i, ...values, reason } : i)),
      );
    } else {
      setItems((prev) => {
        const id = nextId(prev);
        const newItem: RadarItem = { id, ...values, reason };
        return [...prev, newItem];
      });
    }
    closeForm();
  };

  const deleteItem = () => {
    if (!editingItem) return;
    const id = editingItem.id;
    setItems((prev) => prev.filter((i) => i.id !== id));
    closeForm();
  };

  const counts = countStatuses(items);
  const p1Count = items.filter((i) => i.priority === 'P1').length;
  const total = items.length;
  const allDone = total > 0 && counts.done === total;
  const isMorning = mode === 'morning';

  const headerSubtitle = isMorning
    ? `Good morning — ${pluralize(counts.todo, 'new item')} to file.`
    : `Good evening — ${pluralize(counts.inProgress, 'item')} waiting for review.`;

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%', overflow: 'hidden', fontFamily: 'var(--font-sans)' }}>
      <Sidebar
        header={
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 8px 18px' }}>
            <span
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                background: 'var(--brand-500)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontWeight: 700,
                fontSize: 13,
                flexShrink: 0,
              }}
            >
              A
            </span>
            <span
              style={{
                font: 'var(--text-label-md)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-label-md)',
                color: 'var(--text-on-dark)',
              }}
            >
              Astra
            </span>
          </div>
        }
      >
        {NAV_ITEMS.map((label) => (
          <NavItem key={label} active={label === 'Daily Radar'}>
            {label}
          </NavItem>
        ))}
      </Sidebar>

      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          padding: '28px 32px',
          gap: 20,
          background: 'var(--bg-page-tint)',
          minWidth: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexShrink: 0 }}>
          <div>
            <h1 style={{ margin: 0, font: '600 1.5rem/2rem var(--font-sans)', letterSpacing: '-0.005em', color: 'var(--text-strong)' }}>
              Daily Radar
            </h1>
            <p style={{ margin: '2px 0 0', font: 'var(--text-paragraph-sm)', color: 'var(--gray-600)' }}>
              {headerSubtitle}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <SegmentedControl
              options={MODE_OPTIONS}
              value={mode}
              onChange={(id) => setMode(id as Mode)}
            />
            <Button
              variant="secondary"
              onClick={() => setActivePanel((p) => (p === 'connections' ? null : 'connections'))}
            >
              Connections
            </Button>
            <Button variant="primary" onClick={openCreateForm}>
              New Item
            </Button>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <KPICard label="Items Today" value={total} style={{ width: 176 }} />
            <KPICard label="P1" value={p1Count} style={{ width: 176 }} />
            <KPICard label="Done Today" value={counts.done} style={{ width: 176 }} />
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <StatusChip status="pending" style={{ cursor: 'pointer' }} onClick={() => pulseFolder('todo')}>
              To Do · {counts.todo}
            </StatusChip>
            <StatusChip status="inProgress" style={{ cursor: 'pointer' }} onClick={() => pulseFolder('inProgress')}>
              In Progress · {counts.inProgress}
            </StatusChip>
            <StatusChip status="active" style={{ cursor: 'pointer' }} onClick={() => pulseFolder('done')}>
              Done · {counts.done}
            </StatusChip>
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 14, minHeight: 0 }}>
          {allDone ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                background: 'var(--status-success-bg)',
                border: '1px solid var(--green-200)',
                borderRadius: 'var(--radius-xl)',
                padding: '12px 16px',
                flexShrink: 0,
              }}
            >
              <CheckIcon />
              <span style={{ font: 'var(--text-label-sm)', color: 'var(--green-700)' }}>
                All caught up — every item is filed and done.
              </span>
            </div>
          ) : null}

          <KanbanBoard
            items={items}
            onItemsChange={handleItemsChange}
            pulseCol={pulseCol}
            onEditItem={openEditForm}
          />
        </div>
      </div>

      <div
        style={{
          width: activePanel ? '400px' : '0px',
          overflow: 'hidden',
          transition: 'var(--transition-sidebar)',
          flexShrink: 0,
          height: '100%',
        }}
      >
        {activePanel === 'connections' ? (
          <ConnectionsPanel
            connections={connections}
            rechecking={rechecking}
            onToggle={toggleConnection}
            onRecheckAll={recheckAll}
          />
        ) : activePanel === 'itemForm' ? (
          <ItemFormPanel
            key={editingItem ? editingItem.id : 'create'}
            mode={editingItem ? 'edit' : 'create'}
            initialValues={
              editingItem
                ? {
                    priority: editingItem.priority,
                    source: editingItem.source,
                    sender: editingItem.sender,
                    subject: editingItem.subject,
                    time: editingItem.time,
                    status: editingItem.status,
                    reason: editingItem.reason ?? '',
                    carried: editingItem.carried ?? false,
                  }
                : EMPTY_FORM_VALUES
            }
            onSave={saveItem}
            onCancel={closeForm}
            onDelete={editingItem ? deleteItem : undefined}
          />
        ) : null}
      </div>
    </div>
  );
}
