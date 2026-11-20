import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ticketService, metadataService } from '../../services/ticketService';
import { StatusBadge, PriorityBadge } from '../../components/tickets/StatusBadge';
import { TicketSearchBar, filterTickets } from '../../components/tickets/TicketSearchBar';
import type { Ticket, StaffEngineer } from '../../types';
import { Eye, RefreshCw, Users } from 'lucide-react';

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { dateStyle: 'medium' });

export const TeamLeadDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [engineers, setEngineers] = useState<StaffEngineer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [assigningId, setAssigningId] = useState<number | null>(null);
  const [selectedEngineer, setSelectedEngineer] = useState<Record<number, number | ''>>({});

  const loadAll = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([ticketService.listTickets(), metadataService.getEngineers()])
      .then(([t, e]) => { setTickets(t); setEngineers(e); })
      .catch(() => setError('Failed to load data.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const filteredTickets = useMemo(() => {
    return filterTickets(tickets, searchQuery);
  }, [tickets, searchQuery]);

  const handleAssign = async (ticketId: number) => {
    const engineerId = selectedEngineer[ticketId];
    if (!engineerId) return;
    setAssigningId(ticketId);
    try {
      await ticketService.assignTicket(ticketId, { assigned_engineer_id: Number(engineerId) });
      setSelectedEngineer((prev) => ({ ...prev, [ticketId]: '' }));
      loadAll();
    } catch (err: unknown) {
      alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to assign.');
    } finally {
      setAssigningId(null);
    }
  };

  const unassigned = tickets.filter((t) => t.status === 'APPROVED_FOR_ROUTING');
  const inProgress = tickets.filter((t) => t.status === 'IN_PROGRESS');
  const clustered = tickets.filter((t) => t.incident_cluster_id != null);

  const engineerWorkloads = useMemo(() => {
    return engineers.map((eng) => {
      const active = tickets.filter(
        (t) => t.assigned_engineer_id === eng.id && (t.status === 'ASSIGNED' || t.status === 'IN_PROGRESS')
      ).length;
      return {
        ...eng,
        activeCount: active,
      };
    });
  }, [engineers, tickets]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs text-qm-text2 uppercase tracking-wider font-semibold mb-1">Team Lead</p>
          <h1 className="text-2xl font-bold text-qm-text">{user?.full_name}</h1>
          <p className="text-sm text-qm-text2 mt-0.5">{user?.organization_name || user?.organization_code} · Team Queue & Assignment</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Awaiting Assignment', value: unassigned.length, color: 'text-amber-400' },
          { label: 'In Progress', value: inProgress.length, color: 'text-blue-400' },
          { label: 'In Incident Groups', value: clustered.length, color: 'text-rose-400' },
          { label: 'Total Team Tickets', value: tickets.length, color: 'text-qm-text' },
        ].map((s) => (
          <div key={s.label} className="nm-stat">
            <div className="text-xs font-semibold text-qm-text2 uppercase tracking-wider mb-2">{s.label}</div>
            <div className={`text-3xl font-extrabold ${s.color}`}>{loading ? '—' : s.value}</div>
          </div>
        ))}
      </div>

      {/* Solution Helper Workload & Capacity */}
      <div className="nm-card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-qm-primary" />
            <h2 className="text-sm font-semibold text-qm-text">Solution Helper Workload</h2>
          </div>
          <span className="text-xs text-qm-text2 font-medium">{engineers.length} Solution Helpers</span>
        </div>
        {loading ? (
          <div className="text-xs text-qm-text2">Loading workloads...</div>
        ) : engineerWorkloads.length === 0 ? (
          <div className="text-xs text-qm-text2">No solution helpers found in team.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {engineerWorkloads.map((eng) => (
              <div key={eng.id} className="nm-recessed p-3 flex items-center justify-between">
                <div className="truncate mr-2">
                  <p className="text-xs font-semibold text-qm-text truncate">{eng.full_name}</p>
                  <p className="text-[11px] text-qm-text2 truncate">{eng.email}</p>
                </div>
                <div className="text-right shrink-0">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border ${
                    eng.activeCount > 3 ? 'bg-rose-500/10 text-rose-300 border-rose-500/20' :
                    eng.activeCount > 0 ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20' :
                    'bg-slate-500/10 text-slate-400 border-slate-500/20'
                  }`}>
                    {eng.activeCount} active
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main Table */}
      <div className="nm-card overflow-hidden">
        <div className="px-5 py-4 border-b border-qm-border flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-qm-text">Team Queue — Assignment Dispatch</h2>
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
            <button onClick={loadAll} className="flex items-center gap-1.5 text-xs text-qm-text2 hover:text-qm-text font-medium transition-colors whitespace-nowrap">
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
          <div className="py-12 text-center text-sm text-qm-text2">No tickets in team queue.</div>
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
                  {['Ticket #', 'Subject', 'Priority', 'Status', 'Assigned To', 'Created', 'Assign To', ''].map((h) => (
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
                          <Users className="w-3 h-3" /> Incident
                        </span>
                      )}
                    </td>
                    <td><PriorityBadge priority={t.confirmed_priority ?? t.impact} /></td>
                    <td><StatusBadge status={t.status} /></td>
                    <td className="text-qm-text2">{t.assigned_engineer_name ?? <span className="text-slate-600">Unassigned</span>}</td>
                    <td className="text-qm-text2 whitespace-nowrap">{formatDate(t.created_at)}</td>
                    <td>
                      {(t.status === 'APPROVED_FOR_ROUTING' || t.status === 'ASSIGNED' || t.status === 'IN_PROGRESS') ? (
                        <div className="flex items-center gap-2">
                          <select
                            value={selectedEngineer[t.id] ?? ''}
                            onChange={(e) => setSelectedEngineer((prev) => ({ ...prev, [t.id]: e.target.value ? Number(e.target.value) : '' }))}
                            className="nm-input px-2 py-1.5 text-xs min-w-28"
                          >
                            <option value="">— Select Helper —</option>
                            {engineers.map((eng) => (
                              <option key={eng.id} value={eng.id}>
                                {eng.full_name} {eng.id === t.assigned_engineer_id ? '(Assigned)' : ''}
                              </option>
                            ))}
                          </select>
                          <button
                            onClick={() => handleAssign(t.id)}
                            disabled={!selectedEngineer[t.id] || assigningId === t.id}
                            className="px-2.5 py-1.5 text-xs font-semibold text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg border border-amber-500/20 disabled:opacity-40 whitespace-nowrap transition-colors"
                          >
                            {assigningId === t.id ? '...' : t.assigned_engineer_id ? 'Reassign' : 'Assign'}
                          </button>
                        </div>
                      ) : <span className="text-qm-text2/50 text-xs">—</span>}
                    </td>
                    <td>
                      <button onClick={() => navigate(`/tickets/${t.id}`)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-qm-primary bg-qm-primary/10 hover:bg-qm-primary/20 rounded-lg border border-qm-primary/20 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" /> View
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
