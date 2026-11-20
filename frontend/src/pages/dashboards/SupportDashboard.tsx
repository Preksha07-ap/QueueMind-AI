import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ticketService } from '../../services/ticketService';
import { StatusBadge, PriorityBadge } from '../../components/tickets/StatusBadge';
import { TicketSearchBar, filterTickets } from '../../components/tickets/TicketSearchBar';
import type { Ticket } from '../../types';
import { Eye, RefreshCw, X, Users, CheckCircle2, Play } from 'lucide-react';

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { dateStyle: 'medium' });

interface ResolveModalProps {
  ticket: Ticket;
  onConfirm: (resolution: string) => void;
  onClose: () => void;
  loading: boolean;
}

const ResolveModal: React.FC<ResolveModalProps> = ({ ticket, onConfirm, onClose, loading }) => {
  const [text, setText] = useState('');
  return (
    <div className="fixed inset-0 nm-overlay flex items-center justify-center z-50 p-4">
      <div className="nm-raised w-full max-w-md p-6 animate-fade-in">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-qm-text">Mark as Resolved</h3>
            <p className="text-xs text-qm-text2 mt-0.5 font-mono">{ticket.ticket_number}</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-qm-raised rounded-lg text-qm-text2 hover:text-qm-text transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-sm text-qm-text font-medium mb-3">{ticket.subject}</p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          placeholder="Describe the steps taken to resolve this issue..."
          className="nm-input w-full p-3 text-sm resize-y"
        />
        <div className="flex justify-end gap-3 mt-4">
          <button onClick={onClose} className="nm-btn-secondary px-4 py-2 text-xs">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(text)}
            disabled={!text.trim() || loading}
            className="px-5 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl transition-all shadow-md shadow-emerald-600/20"
          >
            {loading ? 'Resolving...' : 'Confirm Resolved'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const SupportDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'assigned' | 'team'>('assigned');
  const [searchQuery, setSearchQuery] = useState('');
  const [resolvingTicket, setResolvingTicket] = useState<Ticket | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadTickets = useCallback(() => {
    setLoading(true);
    setError(null);
    ticketService.listTickets()
      .then(setTickets)
      .catch(() => setError('Failed to load tickets.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadTickets(); }, [loadTickets]);

  const myTickets = tickets.filter((t) => t.assigned_engineer_id === user?.id);
  const teamTickets = tickets.filter((t) =>
    t.status === 'ASSIGNED' || t.status === 'IN_PROGRESS' || t.status === 'APPROVED_FOR_ROUTING'
  );
  const displayed = tab === 'assigned' ? myTickets : teamTickets;

  const filteredTickets = useMemo(() => {
    return filterTickets(displayed, searchQuery);
  }, [displayed, searchQuery]);

  const handleStartWorking = async (ticket: Ticket) => {
    setActionLoading(true);
    try {
      await ticketService.updateStatus(ticket.id, { status: 'IN_PROGRESS', note: 'Engineer started working.' });
      loadTickets();
    } catch { alert('Failed to update status.'); }
    finally { setActionLoading(false); }
  };

  const handleResolve = async (resolution: string) => {
    if (!resolvingTicket || !resolution.trim()) return;
    setActionLoading(true);
    try {
      await ticketService.resolveTicket(resolvingTicket.id, { resolution });
      setResolvingTicket(null);
      loadTickets();
    } catch { alert('Failed to resolve ticket.'); }
    finally { setActionLoading(false); }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {resolvingTicket && (
        <ResolveModal ticket={resolvingTicket} onConfirm={handleResolve} onClose={() => setResolvingTicket(null)} loading={actionLoading} />
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs text-qm-text2 uppercase tracking-wider font-semibold mb-1">Solution Helper</p>
          <h1 className="text-2xl font-bold text-qm-text">{user?.full_name}</h1>
          <p className="text-sm text-qm-text2 mt-0.5">{user?.organization_name || user?.organization_code} · Assigned Tickets</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Assigned to Me', value: myTickets.length, color: 'text-qm-text' },
          { label: 'In Progress', value: myTickets.filter((t) => t.status === 'IN_PROGRESS').length, color: 'text-qm-warning' },
          { label: 'Resolved by Me', value: myTickets.filter((t) => t.status === 'RESOLVED' || t.status === 'CLOSED').length, color: 'text-qm-success' },
        ].map((s) => (
          <div key={s.label} className="nm-stat">
            <div className="text-xs font-semibold text-qm-text2 uppercase tracking-wider mb-2">{s.label}</div>
            <div className={`text-3xl font-extrabold ${s.color}`}>{loading ? '—' : s.value}</div>
          </div>
        ))}
      </div>

      {/* Main Table Card */}
      <div className="nm-card overflow-hidden">
        <div className="px-5 py-4 border-b border-qm-border flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex gap-1 p-1 nm-recessed rounded-xl">
              {(['assigned', 'team'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`nm-tab ${tab === t ? 'nm-tab-active' : ''}`}
                >
                  {t === 'assigned' ? 'My Assigned' : 'Team Queue'}
                </button>
              ))}
            </div>
            <TicketSearchBar
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Search tickets by ID, subject, keywords..."
              className="max-w-xs"
            />
            {searchQuery.trim() && (
              <span className="text-xs text-qm-text2">({filteredTickets.length} of {displayed.length})</span>
            )}
          </div>
          <button
            onClick={loadTickets}
            className="flex items-center gap-1.5 text-xs text-qm-text2 hover:text-qm-text font-medium transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 nm-spinner" />
          </div>
        ) : error ? (
          <div className="py-10 text-center text-sm text-red-400">{error}</div>
        ) : displayed.length === 0 ? (
          <div className="py-12 text-center text-sm text-qm-text2">
            {tab === 'assigned' ? 'No tickets assigned to you.' : 'No tickets in team queue.'}
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
                  {['Ticket #', 'Subject', 'Priority', 'Status', 'Submitter', 'Date', 'Actions'].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredTickets.map((t) => (
                  <tr key={t.id}>
                    <td className="font-mono text-xs text-qm-text2">{t.ticket_number}</td>
                    <td className="font-medium text-qm-text max-w-xs">
                      <span className="line-clamp-1">{t.subject}</span>
                      {t.incident_cluster_id && (
                        <span className="ml-2 inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/20">
                          <Users className="w-3 h-3" /> Cluster
                        </span>
                      )}
                    </td>
                    <td><PriorityBadge priority={t.confirmed_priority ?? t.impact} /></td>
                    <td><StatusBadge status={t.status} /></td>
                    <td className="text-qm-text2">{t.submitted_by_name ?? '—'}</td>
                    <td className="text-qm-text2 whitespace-nowrap">{formatDate(t.updated_at)}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        {t.status === 'ASSIGNED' && t.assigned_engineer_id === user?.id && (
                          <button
                            onClick={() => handleStartWorking(t)}
                            disabled={actionLoading}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/20 disabled:opacity-40 whitespace-nowrap transition-colors"
                          >
                            <Play className="w-3 h-3" /> Start Working
                          </button>
                        )}
                        {t.status === 'IN_PROGRESS' && t.assigned_engineer_id === user?.id && (
                          <button
                            onClick={() => setResolvingTicket(t)}
                            disabled={actionLoading}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-lg border border-emerald-500/20 disabled:opacity-40 whitespace-nowrap transition-colors"
                          >
                            <CheckCircle2 className="w-3 h-3" /> Resolve
                          </button>
                        )}
                        <button
                          onClick={() => navigate(`/tickets/${t.id}`)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-qm-primary bg-qm-primary/10 hover:bg-qm-primary/20 rounded-lg border border-qm-primary/20 transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" /> View
                        </button>
                      </div>
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
