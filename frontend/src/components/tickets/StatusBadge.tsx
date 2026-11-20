import React from 'react';
import type { TicketStatus, TicketPriority } from '../../types';

const STATUS_CONFIG: Record<TicketStatus, { label: string; bg: string; text: string; border: string; dot?: string }> = {
  SUBMITTED:                 { label: 'Submitted',       bg: 'bg-slate-500/10', text: 'text-slate-300',   border: 'border-slate-500/20',  dot: 'bg-slate-400' },
  AI_ANALYSIS:               { label: 'AI Analysis',     bg: 'bg-qm-secondary/10', text: 'text-purple-300', border: 'border-qm-secondary/20', dot: 'bg-qm-secondary' },
  AWAITING_HELP_DESK_REVIEW: { label: 'Awaiting Review', bg: 'bg-amber-500/10', text: 'text-amber-300',   border: 'border-amber-500/20',  dot: 'bg-amber-400' },
  APPROVED_FOR_ROUTING:      { label: 'Approved',        bg: 'bg-qm-primary/10', text: 'text-blue-300',   border: 'border-qm-primary/20', dot: 'bg-qm-primary' },
  ASSIGNED:                  { label: 'Assigned',        bg: 'bg-indigo-500/10', text: 'text-indigo-300', border: 'border-indigo-500/20', dot: 'bg-indigo-400' },
  IN_PROGRESS:               { label: 'In Progress',     bg: 'bg-qm-cyan/10', text: 'text-cyan-300',     border: 'border-qm-cyan/20',   dot: 'bg-qm-cyan' },
  WAITING_FOR_USER:          { label: 'Waiting',         bg: 'bg-orange-500/10', text: 'text-orange-300', border: 'border-orange-500/20', dot: 'bg-orange-400' },
  RESOLVED:                  { label: 'Resolved',        bg: 'bg-emerald-500/10', text: 'text-emerald-300', border: 'border-emerald-500/20', dot: 'bg-emerald-400' },
  CLOSED:                    { label: 'Closed',          bg: 'bg-slate-600/10', text: 'text-slate-500',   border: 'border-slate-600/20',  dot: 'bg-slate-500' },
  REOPENED:                  { label: 'Reopened',        bg: 'bg-red-500/10', text: 'text-red-300',       border: 'border-red-500/20',    dot: 'bg-red-400' },
};

const PRIORITY_CONFIG: Record<TicketPriority, { label: string; bg: string; text: string; glow?: string }> = {
  CRITICAL: { label: 'CRITICAL', bg: 'bg-red-500/15',    text: 'text-red-400',    glow: 'animate-pulse-glow' },
  HIGH:     { label: 'HIGH',     bg: 'bg-orange-500/15', text: 'text-orange-400' },
  MEDIUM:   { label: 'MEDIUM',   bg: 'bg-amber-500/15',  text: 'text-amber-400' },
  LOW:      { label: 'LOW',      bg: 'bg-slate-500/15',  text: 'text-slate-400' },
};

interface StatusBadgeProps { status: TicketStatus; }
interface PriorityBadgeProps { priority: TicketPriority | string | null | undefined; }

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const cfg = STATUS_CONFIG[status] ?? { label: status, bg: 'bg-slate-500/10', text: 'text-slate-300', border: 'border-slate-500/20', dot: 'bg-slate-400' };
  return (
    <span className={`nm-badge gap-1.5 ${cfg.bg} ${cfg.text} border ${cfg.border}`}>
      {cfg.dot && <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />}
      {cfg.label}
    </span>
  );
};

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority }) => {
  if (!priority) return <span className="text-slate-600 text-xs">—</span>;
  const cfg = PRIORITY_CONFIG[priority as TicketPriority] ?? { label: priority, bg: 'bg-slate-500/15', text: 'text-slate-400' };
  return (
    <span className={`nm-badge ${cfg.bg} ${cfg.text} ${cfg.glow || ''}`}>
      {cfg.label}
    </span>
  );
};
