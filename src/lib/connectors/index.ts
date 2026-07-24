// Read-only ingestion: this module only ever reads already-pulled Outlook/Slack data and
// classifies it. It must never call anything that sends, replies to, edits, archives, or deletes a message.
import { RadarItem } from '../data';
import { classify } from '../rankingRules';
import { RAW_OUTLOOK_MESSAGES, RAW_SLACK_MESSAGES } from './snapshot';

function stripEmoji(text: string): string {
  return text
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F1E6}-\u{1F1FF}]/gu, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function formatTimeIst(iso: string): string {
  const formatted = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Kolkata',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(iso));
  // Normalize "9:07 am" / "9:07 AM"-style output to the app's "9:07 AM" pattern.
  return formatted.replace(/\s*([AaPp][Mm])$/, ' $1').toUpperCase();
}

interface MergedEntry {
  item: Omit<RadarItem, 'id'>;
  sortKey: number;
}

export function buildConnectorItems(): RadarItem[] {
  const outlookEntries: MergedEntry[] = RAW_OUTLOOK_MESSAGES.map((m) => {
    const subject = stripEmoji(m.subject);
    const classification = classify({
      text: subject,
      senderHandle: m.senderEmail,
      importanceHigh: m.importanceHigh,
    });
    return {
      sortKey: new Date(m.receivedAtIso).getTime(),
      item: {
        priority: classification.priority,
        source: 'Outlook',
        sender: m.senderLabel,
        subject,
        time: formatTimeIst(m.receivedAtIso),
        status: 'todo',
        carried: false,
        reason: classification.priority === 'P1' ? m.reasonIfP1 : undefined,
      },
    };
  });

  const slackEntries: MergedEntry[] = RAW_SLACK_MESSAGES.map((m) => {
    const text = stripEmoji(m.text);
    const classification = classify({
      text,
      senderHandle: m.senderLabel,
      isDirectMessage: m.isDirectMessage,
    });
    return {
      sortKey: new Date(m.sentAtIso).getTime(),
      item: {
        priority: classification.priority,
        source: 'Slack',
        sender: m.senderLabel,
        subject: text,
        time: formatTimeIst(m.sentAtIso),
        status: 'todo',
        carried: false,
        reason: classification.priority === 'P1' ? m.reasonIfP1 : undefined,
      },
    };
  });

  return [...outlookEntries, ...slackEntries]
    .sort((a, b) => a.sortKey - b.sortKey)
    .map((entry, index) => ({ id: index + 1, ...entry.item }));
}
