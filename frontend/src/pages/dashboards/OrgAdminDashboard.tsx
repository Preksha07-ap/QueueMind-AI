import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import { ticketService } from '../../services/ticketService';
import { StatusBadge, PriorityBadge } from '../../components/tickets/StatusBadge';
import { TicketSearchBar, filterTickets } from '../../components/tickets/TicketSearchBar';
import type { User as UserType, IncidentCluster, Ticket } from '../../types';
import { Users, Building2, Layers, RefreshCw, AlertTriangle, Ticket as TicketIcon, Eye } from 'lucide-react';

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { dateStyle: 'medium' });

export const OrgAdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [usersList, setUsersList] = useState<UserType[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'tickets' | 'users'>('overview');
  const [clusters, setClusters] = useState<IncidentCluster[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoadingTickets, setIsLoadingTickets] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchUsers = async () => {
    setIsLoadingUsers(true);
    try {
      const response = await api.get<UserType[]>('/users');
      setUsersList(response.data);
    } catch {
      // silent
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const fetchClusters = async () => {
    try {
      const data = await ticketService.listIncidentClusters();
      setClusters(data as IncidentCluster[]);
    } catch {
      setClusters([]);
    }
  };

  const fetchTickets = async () => {
    setIsLoadingTickets(true);
    try {
      const data = await ticketService.listTickets();
      setTickets(data);
    } catch {
      setTickets([]);
    } finally {
      setIsLoadingTickets(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchClusters();
    fetchTickets();
  }, []);

  const filteredTickets = useMemo(() => {
    return filterTickets(tickets, searchQuery);
  }, [tickets, searchQuery]);

  const ROLE_COLOR: Record<string, string> = {
    USER: 'text-qm-text2 bg-slate-500/10 border-slate-500/20',
    HELP_DESK: 'text-qm-cyan bg-cyan-500/10 border-cyan-500/20',
    SUPPORT_TEAM_MEMBER: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    SUPPORT_TEAM_LEAD: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    ORGANIZATION_ADMIN: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
    PLATFORM_OWNER: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <p className="text-xs text-qm-text2 uppercase tracking-wider font-semibold mb-1">Organisation Admin</p>
        <h1 className="text-2xl font-bold text-qm-text">{user?.full_name}</h1>
        <p className="text-sm text-qm-text2 mt-0.5">
          {user?.organization_name || user?.organization_code}
          {user?.organization_code && <span className="ml-2 font-mono text-xs text-qm-text2/70">({user.organization_code})</span>}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 nm-recessed rounded-xl w-fit">
        <button
          onClick={() => setActiveTab('overview')}
          className={`nm-tab ${activeTab === 'overview' ? 'nm-tab-active' : ''}`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('tickets')}
          className={`nm-tab flex items-center gap-1.5 ${activeTab === 'tickets' ? 'nm-tab-active' : ''}`}
        >
          <TicketIcon className="w-3.5 h-3.5" />
          Organisation Tickets ({tickets.length})
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`nm-tab flex items-center gap-1.5 ${activeTab === 'users' ? 'nm-tab-active' : ''}`}
        >
          <Users className="w-3.5 h-3.5" />
          Members ({usersList.length})
        </button>
      </div>

      {activeTab === 'overview' ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: TicketIcon, label: 'Organisation Tickets', desc: 'Browse and search all submitted tickets across the organisation.', action: () => setActiveTab('tickets'), actionLabel: 'View tickets →' },
              { icon: Users, label: 'User Management', desc: 'Manage accounts, roles and access for your organisation members.', action: () => setActiveTab('users'), actionLabel: 'View members →' },
              { icon: Building2, label: 'Departments', desc: 'Configure IT, Examination, Accounts and other departments.', action: null, actionLabel: 'Configure →' },
              { icon: Layers, label: 'Support Teams', desc: 'Set up specialized teams: Network, Hardware, Fee Support.', action: null, actionLabel: 'Configure →' },
            ].map((card) => (
              <div key={card.label} className="nm-card p-5">
                <div className="w-9 h-9 rounded-lg bg-qm-raised border border-qm-border flex items-center justify-center mb-3">
                  <card.icon className="w-5 h-5 text-qm-primary" />
                </div>
                <h3 className="text-sm font-semibold text-qm-text">{card.label}</h3>
                <p className="mt-1 text-xs text-qm-text2 leading-relaxed">{card.desc}</p>
                <button
                  onClick={card.action ?? undefined}
                  disabled={!card.action}
                  className="mt-3 text-xs font-semibold text-qm-primary hover:text-qm-primary/80 disabled:text-qm-text2/40 disabled:cursor-not-allowed transition-colors"
                >
                  {card.actionLabel}
                </button>
              </div>
            ))}
          </div>

          {/* Incident Clusters Summary */}
          {clusters.length > 0 && (
            <div className="nm-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <h2 className="text-sm font-semibold text-qm-text">Active Incident Groups</h2>
                <span className="ml-auto text-xs text-qm-text2">{clusters.length} cluster{clusters.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {clusters.slice(0, 6).map((cl) => (
                  <div key={cl.id} className="nm-recessed p-3.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-qm-primary font-bold">{cl.cluster_number}</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                        cl.incident_priority === 'CRITICAL' ? 'bg-red-500/10 text-red-300 border-red-500/20' :
                        cl.incident_priority === 'HIGH' ? 'bg-amber-500/10 text-amber-300 border-amber-500/20' :
                        cl.incident_priority === 'MEDIUM' ? 'bg-yellow-500/10 text-yellow-300 border-yellow-500/20' :
                        'bg-slate-500/10 text-slate-400 border-slate-500/20'
                      }`}>{cl.incident_priority}</span>
                    </div>
                    {cl.common_issue_summary && (
                      <p className="text-xs text-qm-text line-clamp-2">{cl.common_issue_summary}</p>
                    )}
                    <div className="flex items-center gap-3 text-[11px] text-qm-text2">
                      <span className="flex items-center gap-1"><Users className="w-3 h-3" />{cl.distinct_affected_users} user{cl.distinct_affected_users !== 1 ? 's' : ''}</span>
                      <span>{cl.total_reports} report{cl.total_reports !== 1 ? 's' : ''}</span>
                      <span className="ml-auto capitalize text-emerald-400">{cl.status.toLowerCase()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : activeTab === 'tickets' ? (
        <div className="nm-card overflow-hidden">
          <div className="px-5 py-4 border-b border-qm-border flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <TicketIcon className="w-4 h-4 text-qm-primary" />
              <h3 className="text-sm font-semibold text-qm-text">Organisation Tickets</h3>
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
                onClick={fetchTickets}
                className="p-2 text-qm-text2 hover:text-qm-text rounded-lg hover:bg-qm-raised transition-colors"
                title="Refresh tickets"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingTickets ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {isLoadingTickets ? (
            <div className="flex items-center justify-center py-16">
              <div className="w-8 h-8 nm-spinner" />
            </div>
          ) : tickets.length === 0 ? (
            <div className="py-12 text-center text-sm text-qm-text2">No tickets found in this organisation.</div>
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
                    {['Ticket #', 'Subject', 'Category', 'Priority', 'Status', 'Submitter', 'Created', ''].map((h) => (
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
                      </td>
                      <td className="text-qm-text2">{t.category_name ?? t.ai_predicted_category ?? '—'}</td>
                      <td><PriorityBadge priority={t.confirmed_priority ?? t.impact} /></td>
                      <td><StatusBadge status={t.status} /></td>
                      <td className="text-qm-text2">{t.submitted_by_name ?? '—'}</td>
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
      ) : (
        <div className="nm-card overflow-hidden">
          <div className="px-5 py-4 border-b border-qm-border flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-qm-text">Organisation Members</h3>
              <p className="text-xs text-qm-text2 mt-0.5">Filtered strictly by your organisation ID</p>
            </div>
            <button onClick={fetchUsers} className="p-2 text-qm-text2 hover:text-qm-text rounded-lg hover:bg-qm-raised transition-colors">
              <RefreshCw className={`w-4 h-4 ${isLoadingUsers ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {isLoadingUsers ? (
            <div className="flex items-center justify-center py-16">
              <div className="w-8 h-8 nm-spinner" />
            </div>
          ) : usersList.length === 0 ? (
            <div className="py-12 text-center text-sm text-qm-text2">No users found in this organisation.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="nm-table">
                <thead>
                  <tr>
                    {['Full Name', 'Email', 'Role', 'Status'].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {usersList.map((u) => (
                    <tr key={u.id}>
                      <td className="font-semibold text-qm-text">{u.full_name}</td>
                      <td className="text-qm-text2">{u.email}</td>
                      <td>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-mono font-semibold border ${ROLE_COLOR[u.role] ?? 'text-qm-text2 bg-slate-500/10 border-slate-500/20'}`}>
                          {u.role}
                        </span>
                      </td>
                      <td>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${u.account_status === 'ACTIVE' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20'}`}>
                          {u.account_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
