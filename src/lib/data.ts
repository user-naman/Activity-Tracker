export type Priority = 'P1' | 'P2' | 'P3';
export type Source = 'Gmail' | 'Outlook' | 'Teams' | 'Fireflies';
export type Status = 'todo' | 'inProgress' | 'done';

export interface RadarItem {
  id: number;
  priority: Priority;
  source: Source;
  sender: string;
  time: string;
  subject: string;
  status: Status;
  reason?: string;
  carried?: boolean;
}

export interface SourceMeta {
  initial: string;
  color: string;
  bg: string;
}

export interface PriorityMeta {
  tone: 'danger' | 'warning' | 'info';
}

export interface StatusMetaEntry {
  label: string;
  dot: string;
}

export const SOURCE_META: Record<Source, SourceMeta> = {
  Gmail: { initial: 'G', color: '#d02533', bg: '#ffeaeb' },
  Outlook: { initial: 'O', color: '#2547d0', bg: '#eaf1ff' },
  Teams: { initial: 'T', color: '#5b2cc9', bg: '#eeeaff' },
  Fireflies: { initial: 'F', color: '#ce5e12', bg: '#fff3eb' },
};

export const PRIORITY_META: Record<Priority, PriorityMeta> = {
  P1: { tone: 'danger' },
  P2: { tone: 'warning' },
  P3: { tone: 'info' },
};

export const STATUS_META: Record<Status, StatusMetaEntry> = {
  todo: { label: 'To Do', dot: '#f5b41d' },
  inProgress: { label: 'In Progress', dot: '#335cff' },
  done: { label: 'Done', dot: '#1fc16b' },
};

export const BASE_ITEMS: RadarItem[] = [
  {
    id: 1,
    priority: 'P1',
    source: 'Gmail',
    sender: 'Sarah Chen',
    time: '8:12 AM',
    subject: 'Contract renewal deadline moved up',
    status: 'todo',
    reason: 'Renewal now closes in 3 days — signature still pending on your side.',
  },
  {
    id: 2,
    priority: 'P2',
    source: 'Outlook',
    sender: 'James Patel',
    time: '8:45 AM',
    subject: 'Budget approval needed for Q3 sourcing',
    status: 'todo',
  },
  {
    id: 3,
    priority: 'P1',
    source: 'Teams',
    sender: 'Lena Ortiz',
    time: '9:03 AM',
    subject: 'Vendor escalation flagged as urgent',
    status: 'inProgress',
    reason: 'Vendor is holding delivery until the pricing dispute is resolved.',
  },
  {
    id: 4,
    priority: 'P3',
    source: 'Fireflies',
    sender: 'Call recap',
    time: '9:30 AM',
    subject: 'Sourcing sync notes are ready to review',
    status: 'done',
  },
  {
    id: 5,
    priority: 'P2',
    source: 'Gmail',
    sender: 'Marcus Webb',
    time: '10:15 AM',
    subject: 'RFQ response received from vendor',
    status: 'todo',
  },
  {
    id: 6,
    priority: 'P1',
    source: 'Outlook',
    sender: 'Priya Nair',
    time: '11:02 AM',
    subject: 'Legal flagged a clause in the draft MSA',
    status: 'inProgress',
    reason: 'Indemnity clause blocks sign-off — legal needs a decision from you today.',
  },
  {
    id: 7,
    priority: 'P3',
    source: 'Teams',
    sender: 'Dana Kim',
    time: '11:40 AM',
    subject: 'FYI: sourcing policy doc was updated',
    status: 'done',
  },
];

export function makeItems(): RadarItem[] {
  return BASE_ITEMS.map((i) => ({ ...i, carried: false }));
}

const PRIORITY_RANK: Record<Priority, number> = { P1: 0, P2: 1, P3: 2 };

function timeToMinutes(time: string): number {
  const match = time.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
  if (!match) return 0;
  let hours = parseInt(match[1], 10);
  const minutes = parseInt(match[2], 10);
  const meridian = match[3].toUpperCase();
  if (meridian === 'PM' && hours !== 12) hours += 12;
  if (meridian === 'AM' && hours === 12) hours = 0;
  return hours * 60 + minutes;
}

export function rankItems(items: RadarItem[]): RadarItem[] {
  return [...items].sort((a, b) => {
    const rankDiff = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
    if (rankDiff !== 0) return rankDiff;
    return timeToMinutes(a.time) - timeToMinutes(b.time);
  });
}

export interface StatusCounts {
  todo: number;
  inProgress: number;
  done: number;
}

export function countStatuses(items: RadarItem[]): StatusCounts {
  const c: StatusCounts = { todo: 0, inProgress: 0, done: 0 };
  items.forEach((i) => {
    c[i.status] += 1;
  });
  return c;
}
