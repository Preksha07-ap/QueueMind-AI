import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ticketService } from '../../services/ticketService';
import { StatusBadge, PriorityBadge } from '../../components/tickets/StatusBadge';
import { TicketSearchBar, filterTickets } from '../../components/tickets/TicketSearchBar';
import type { Ticket, TicketStatus } from '../../types';
import { PlusCircle, Eye, RefreshCw, AlertCircle, Ticket as TicketIcon, Clock, CheckCircle2 } from 'lucide-react';

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { dateStyle: 'medium' });

const OPEN_STATUSES: TicketStatus[] = [
  'SUBMITTED', 'AI_ANALYSIS', 'AWAITING_HELP_DESK_REVIEW',
  'APPROVED_FOR_ROUTING', 'ASSIGNED', 'IN_PROGRESS', 'WAITING_FOR_USER', 'REOPENED',
];

export const UserDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const loadTickets = () => {
    setLoading(true);
    setError(null);
    ticketService
      .listTickets()
      .then(setTickets)
      .catch(() => setError('Failed to load tickets.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadTickets(); }, []);

  const total = tickets.length;
  const open = tickets.filter((t) => OPEN_STATUSES.includes(t.status)).length;
  const resolved = tickets.filter((t) => t.status === 'RESOLVED' || t.status === 'CLOSED').length;

  const filteredTickets = useMemo(() => {
    return filterTickets(tickets, searchQuery);
  }, [tickets, searchQuery]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs text-qm-text2 uppercase tracking-wider font-semibold mb-1">My Workspace</p>
          <h1 className="text-2xl font-bold text-qm-text">{user?.full_name}</h1>
          <p className="text-sm text-qm-text2 mt-0.5">
            {user?.organization_name || user?.organization_code} · {user?.email}
          </p>
        </div>
        <button
          onClick={() => navigate('/tickets/new')}
          className="nm-btn-primary flex items-center gap-2 px-4 py-2.5 text-sm"
        >
          <PlusCircle className="w-4 h-4" />
          Raise New Ticket
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Total Tickets', value: total, color: 'text-qm-text', icon: TicketIcon, border: 'border-qm-border' },
          { label: 'Active Issues', value: open, color: 'text-qm-warning', icon: Clock, border: 'border-qm-warning/20' },
          { label: 'Resolved Tickets', value: resolved, color: 'text-qm-success', icon: CheckCircle2, border: 'border-qm-success/20' },
        ].map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.label} className={`nm-stat border ${s.border}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-qm-text2 uppercase tracking-wider">{s.label}</span>
                <Icon className={`w-4 h-4 ${s.color}`} />
              </div>
              <div className={`text-3xl font-extrabold ${s.color}`}>{loading ? '—' : s.value}</div>
            </div>
          );
        })}
      </div>

      {/* Ticket Table */}
      <div className="nm-card overflow-hidden">
        <div className="px-5 py-4 border-b border-qm-border flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <TicketIcon className="w-4 h-4 text-qm-primary" />
            <h2 className="text-sm font-semibold text-qm-text">My Tickets</h2>
            {searchQuery.trim() && (
              <span className="text-xs text-qm-text2">({filteredTickets.length} of {tickets.length})</span>
            )}
          </div>
          <div className="flex items-center gap-3 flex-1 sm:flex-initial justify-end">
            <TicketSearchBar
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Search tickets by ID, subject, keywords..."
            />
            <button
              onClick={loadTickets}
              className="flex items-center gap-1.5 text-xs text-qm-text2 hover:text-qm-text font-medium transition-colors whitespace-nowrap"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 nm-spinner" />
          </div>
        ) : error ? (
          <div className="py-10 text-center text-sm text-red-400">{error}</div>
        ) : tickets.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-qm-text2 text-sm">No tickets submitted yet.</p>
            <button
              onClick={() => navigate('/tickets/new')}
              className="mt-4 nm-btn-primary inline-flex items-center gap-2 px-5 py-2.5 text-sm"
            >
              <PlusCircle className="w-4 h-4" />
              Raise your first ticket
            </button>
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="py-12 text-center text-sm text-qm-text2">
            <p>No tickets found matching your search.</p>
            <button
              onClick={() => setSearchQuery('')}
              className="mt-2 text-xs text-qm-primary hover:underline font-medium"
            >
              Clear search
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="nm-table">
              <thead>
                <tr>
                  {['Ticket #', 'Subject', 'Category', 'Priority', 'Status', 'Created', ''].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredTickets.map((t) => (
                  <tr key={t.id}>
                    <td className="font-mono text-xs text-qm-text2">{t.ticket_number}</td>
                    <td className="font-medium text-qm-text max-w-xs">
                      <div className="flex items-center gap-1.5">
                        <span className="line-clamp-1">{t.subject}</span>
                        {(t.incident_cluster_id || t.related_incident_id) && (
                          <span
                            title="This issue is affecting other users too"
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 whitespace-nowrap"
                          >
                            <AlertCircle className="w-2.5 h-2.5" />
                            Affecting others
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="text-qm-text2">{t.category_name ?? '—'}</td>
                    <td><PriorityBadge priority={t.confirmed_priority ?? t.impact} /></td>
                    <td><StatusBadge status={t.status} /></td>
                    <td className="text-qm-text2 whitespace-nowrap">{formatDate(t.created_at)}</td>
                    <td>
                      <button
                        onClick={() => navigate(`/tickets/${t.id}`)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-qm-primary bg-qm-primary/10 hover:bg-qm-primary/20 rounded-lg transition-colors border border-qm-primary/20"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
