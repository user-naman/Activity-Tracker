export interface RawOutlookMessage {
  id: number;
  senderLabel: string; // human-readable sender, e.g. "Geetika Chanana" (precomputed, no name-parsing logic)
  senderEmail: string; // real address, used only for the noise-sender rule
  subject: string; // cleaned, single-line, already emoji-free at the source of truth below
  receivedAtIso: string; // UTC ISO timestamp, as returned by the mailbox
  importanceHigh: boolean; // Outlook's own importance flag
  reasonIfP1?: string; // authored one-line "why" — only surfaced if classify() lands on P1
}

export interface RawSlackMessage {
  id: number;
  senderLabel: string;
  text: string;
  sentAtIso: string; // ISO timestamp already in the user's local time zone-equivalent instant (UTC instant is fine — format at render time)
  isDirectMessage: boolean; // true for DM / group DM, false for a channel message
  reasonIfP1?: string;
}
