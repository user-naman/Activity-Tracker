import { Priority } from './data';

export interface ClassificationInput {
  /** Subject line (Outlook) or message text (Slack) — the text keyword rules run against. */
  text: string;
  /** Sender's email address (Outlook) or Slack handle — only used by the noise-sender tier below. */
  senderHandle: string;
  /** Outlook's own "High importance" flag, or any other source's native importance marker. */
  importanceHigh?: boolean;
  /** True for a Slack DM or group DM — a message addressed directly to you, not channel chatter. */
  isDirectMessage?: boolean;
}

export interface Classification {
  priority: Priority;
}

/**
 * Known bulk/marketing senders. Messages from these are always P3, regardless of keywords,
 * so a stray word like "due" in a newsletter footer can't misfire a real signal into P2.
 * Edit this list to mute/unmute senders.
 */
const NOISE_SENDER_PATTERNS: RegExp[] = [
  /^news@/i,
  /^no-reply@/i,
  /^changelog@/i,
  /^googlecloud@/i,
];

/** Any of these words/phrases in the text — an explicit urgency marker. */
const P1_KEYWORDS = /\b(p0|urgent|critical|blocker|asap|escalat\w*)\b/i;

/** Deadlines, approvals, and direct asks — worth doing today, not urgent-urgent. */
const P2_KEYWORDS = /\b(deadline|due|approval|approve|resubmit|submit|reschedul\w*|cancel(l)?ed|feedback|review)\b/i;
const P2_PLEASE = /\bplease\s+(attend|submit|approve|confirm|review|respond|complete)\b/i;
const P2_DATE = /\b(by|before)\s+\d{1,2}\s+\w+\s+\d{4}\b/i;

export function classify(input: ClassificationInput): Classification {
  if (input.importanceHigh) return { priority: 'P1' };
  if (P1_KEYWORDS.test(input.text)) return { priority: 'P1' };
  if (NOISE_SENDER_PATTERNS.some((rx) => rx.test(input.senderHandle))) return { priority: 'P3' };
  if (P2_KEYWORDS.test(input.text) || P2_PLEASE.test(input.text) || P2_DATE.test(input.text)) {
    return { priority: 'P2' };
  }
  if (input.isDirectMessage) return { priority: 'P2' };
  return { priority: 'P3' };
}
