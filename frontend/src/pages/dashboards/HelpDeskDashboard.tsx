import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ticketService, metadataService } from '../../services/ticketService';
import { StatusBadge, PriorityBadge } from '../../components/tickets/StatusBadge';
import { TicketSearchBar, filterTickets } from '../../components/tickets/TicketSearchBar';
import type { Ticket, TicketPriority, Department, SupportTeam, Category, StaffEngineer, IncidentCluster } from '../../types';
import type { TicketRoutePayload } from '../../services/ticketService';
import {
  Eye,
  RefreshCw,
  X,
  Sparkles,
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Users,
  ShieldAlert,
  HelpCircle,
  ArrowUpRight,
  Building2,
  FileCheck,
} from 'lucide-react';

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { dateStyle: 'medium' });

interface RouteModalProps {
  ticket: Ticket;
  departments: Department[];
  onConfirm: (payload: TicketRoutePayload) => void;
  onClose: () => void;
  onEscalate: (ticket: Ticket) => void;
  onRequestClarification: (ticket: Ticket) => void;
  loading: boolean;
}

const RouteModal: React.FC<RouteModalProps> = ({
  ticket,
  departments,
  onConfirm,
  onClose,
  onEscalate,
  onRequestClarification,
  loading,
}) => {
  const [departmentId, setDepartmentId] = useState<number | ''>(ticket.ai_recommended_department_id || '');
  const [teamId, setTeamId] = useState<number | ''>(ticket.ai_recommended_support_team_id || '');
  const [categoryId, setCategoryId] = useState<number | ''>(ticket.category_id || '');
  const [categories, setCategories] = useState<Category[]>([]);
  const [teams, setTeams] = useState<SupportTeam[]>([]);
  const [priority, setPriority] = useState<TicketPriority>(
    ticket.confirmed_priority || (ticket.impact as TicketPriority) || 'MEDIUM'
  );
  const [note, setNote] = useState('');
  const [engineers, setEngineers] = useState<StaffEngineer[]>([]);
  const [assignedEngineerId, setAssignedEngineerId] = useState<number | ''>('');

  useEffect(() => {
    metadataService.getCategories().then(setCategories).catch(() => setCategories([]));
  }, []);

  const evidence = useMemo(() => {
    if (!ticket.ai_evidence_json) return null;
    try {
      return JSON.parse(ticket.ai_evidence_json);
    } catch {
      return null;
    }
  }, [ticket.ai_evidence_json]);

  useEffect(() => {
    if (departmentId) {
      metadataService
        .getSupportTeams(Number(departmentId))
        .then((fetched) => {
          setTeams(fetched);
        })
        .catch(() => setTeams([]));
    } else {
      setTeams([]);
      setTeamId('');
    }
  }, [departmentId]);

  useEffect(() => {
    if (teamId) {
      metadataService
        .getEngineers(Number(teamId))
        .then(setEngineers)
        .catch(() => setEngineers([]));
    } else {
      setEngineers([]);
      setAssignedEngineerId('');
    }
  }, [teamId]);

  const handleApplyAIRecs = () => {
    if (ticket.ai_recommended_department_id) {
      setDepartmentId(ticket.ai_recommended_department_id);
    }
    if (ticket.ai_recommended_support_team_id) {
      setTeamId(ticket.ai_recommended_support_team_id);
    }
    if (ticket.confirmed_priority) {
      setPriority(ticket.confirmed_priority);
    }
  };

  const isAIMatch =
    departmentId === ticket.ai_recommended_department_id &&
    teamId === ticket.ai_recommended_support_team_id &&
    Boolean(departmentId && teamId);

  const clusterInfo = evidence?.incident_cluster;
  const verifiedRes = ticket.verified_resolution || evidence?.rag_solution?.verified_resolution || evidence?.historical_incident?.verified_resolution;
  const routingReason = evidence?.routing?.routing_reason;
  const requiresManualReview = evidence?.routing?.requires_manual_review || (!ticket.ai_recommended_department_id && !ticket.ai_recommended_support_team_id);

  return (
    <div className="fixed inset-0 nm-overlay flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="nm-raised w-full max-w-2xl p-6 my-8 animate-fade-in space-y-4">
        <div className="flex items-center justify-between border-b border-qm-border pb-3">
          <div>
            <h3 className="text-base font-bold text-qm-text">Review & Route Ticket</h3>
            <p className="text-xs text-qm-text2 mt-0.5 font-mono">
              {ticket.ticket_number} — <span className="text-qm-text font-sans font-medium">{ticket.subject}</span>
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-qm-raised rounded-lg text-qm-text2 hover:text-qm-text transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* AI Triage Recommendation Panel */}
        <div className="nm-recessed p-4 space-y-3 border border-qm-primary/20 rounded-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-qm-primary" />
              <span className="text-xs font-bold text-qm-primary uppercase tracking-wide">
                AI Automatic Triage Analysis & Routing Intelligence
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded border ${
                ticket.ai_analysis_status === 'COMPLETED'
                  ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                  : ticket.ai_analysis_status === 'FAILED'
                  ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                  : 'bg-amber-500/10 text-amber-300 border-amber-500/20'
              }`}>
                {ticket.ai_analysis_status || 'PENDING'}
              </span>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-qm-cyan/10 text-qm-cyan border border-qm-cyan/20">
                AI Analysed
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 text-xs">
            <div className="nm-card p-2.5">
              <span className="text-qm-text2 block mb-0.5 text-[11px]">Predicted Category</span>
              <div className="font-semibold text-qm-text truncate">
                {ticket.ai_predicted_category || evidence?.classification?.predicted_category || ticket.category_name || 'General Support'}
              </div>
              {ticket.ai_confidence_score !== null && ticket.ai_confidence_score !== undefined && (
                <span className="text-[10px] text-qm-primary font-mono">
                  {Math.round(ticket.ai_confidence_score * 100)}% conf
                </span>
              )}
            </div>

            <div className="nm-card p-2.5">
              <span className="text-qm-text2 block mb-0.5 text-[11px]">Recommended Team</span>
              <div className="font-semibold text-qm-cyan truncate">
                {ticket.ai_recommended_support_team_name || evidence?.routing?.recommended_support_team_name || 'Manual Review'}
              </div>
              <span className="text-[10px] text-qm-text2 truncate block">
                {ticket.ai_recommended_department_name || evidence?.routing?.recommended_department_name || 'No team configured'}
              </span>
            </div>

            <div className="nm-card p-2.5">
              <span className="text-qm-text2 block mb-0.5 text-[11px]">Impact / Urgency</span>
              <div className="font-semibold text-qm-text">
                <span className="text-qm-primary">{ticket.impact || evidence?.priority?.impact || 'MEDIUM'}</span> /{' '}
                <span className="text-amber-300">{ticket.urgency || evidence?.priority?.urgency || 'MEDIUM'}</span>
              </div>
            </div>

            <div className="nm-card p-2.5">
              <span className="text-qm-text2 block mb-0.5 text-[11px]">Calculated Priority</span>
              <div className="font-semibold text-amber-300 font-mono flex items-center justify-between">
                <span>{ticket.confirmed_priority ?? ticket.ai_predicted_priority ?? 'MEDIUM'}</span>
                {ticket.ai_priority_score !== null && ticket.ai_priority_score !== undefined && (
                  <span className="text-[10px] text-qm-text2 font-mono">
                    {ticket.ai_priority_score} pts
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Routing Reason & Fallback Indicator */}
          {routingReason && (
            <div className={`p-2.5 rounded-lg text-xs border ${
              evidence?.routing?.is_fallback
                ? 'bg-amber-500/10 border-amber-500/20 text-amber-200'
                : requiresManualReview
                ? 'bg-rose-500/10 border-rose-500/20 text-rose-200'
                : 'bg-qm-cyan/10 border-qm-cyan/20 text-qm-cyan'
            }`}>
              <div className="flex items-center gap-1.5 font-semibold mb-0.5">
                <Building2 className="w-3.5 h-3.5" />
                <span>Routing Recommendation Rationale</span>
              </div>
              <p className="text-[11px] opacity-90">{routingReason}</p>
            </div>
          )}

          {/* Priority Explanation */}
          {ticket.ai_priority_explanation && (
            <p className="text-xs text-qm-text2 nm-card p-2.5">
              <strong className="text-qm-text">Priority Justification:</strong> {ticket.ai_priority_explanation}
            </p>
          )}

          {/* Incident Cluster Details */}
          {clusterInfo && (
            <div className="p-2.5 rounded-lg text-xs bg-rose-500/10 border border-rose-500/20 text-rose-200 space-y-1">
              <div className="flex items-center justify-between font-semibold">
                <div className="flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <span>Incident Cluster: {clusterInfo.cluster_number}</span>
                </div>
                <span className="font-mono text-[11px] text-rose-300">
                  {clusterInfo.distinct_affected_users} affected users ({clusterInfo.total_reports} reports)
                </span>
              </div>
              {clusterInfo.common_issue_summary && (
                <p className="text-[11px] text-rose-200/90">{clusterInfo.common_issue_summary}</p>
              )}
            </div>
          )}

          {/* Verified Resolution */}
          {verifiedRes && (
            <div className="p-2.5 rounded-lg text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-emerald-300">
                <FileCheck className="w-4 h-4 text-emerald-400" />
                <span>Verified Historical Resolution Available</span>
              </div>
              <p className="text-[11px] text-emerald-200/90">{verifiedRes}</p>
            </div>
          )}

          {/* Duplicate Warning */}
          {ticket.ai_duplicate_ticket_id && (
            <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-lg text-xs text-amber-200">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Potential Semantic Duplicate Detected</p>
                <p className="text-amber-300/80 text-[11px] mt-0.5">
                  Matches existing Ticket #{ticket.ai_duplicate_ticket_id} with{' '}
                  {Math.round((ticket.ai_duplicate_score || 0) * 100)}% similarity.
                </p>
              </div>
            </div>
          )}

          {/* Suggested KB Resolutions */}
          {evidence?.kb_suggestions && evidence.kb_suggestions.length > 0 && (
            <div className="nm-card p-2.5 space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs text-qm-primary font-medium">
                <BookOpen className="w-3.5 h-3.5" />
                <span>Knowledge Base Suggestions ({evidence.kb_suggestions.length})</span>
              </div>
              <ul className="text-[11px] text-qm-text2 list-disc list-inside space-y-0.5">
                {evidence.kb_suggestions.slice(0, 2).map((m: { title?: string; resolution?: string; snippet?: string }, idx: number) => (
                  <li key={idx} className="truncate">
                    <span className="text-qm-text font-medium">{m.title || 'Solution'}:</span> {m.resolution || m.snippet}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Quick Apply AI Recommendations Button */}
          {ticket.ai_recommended_department_id && !isAIMatch && (
            <div className="pt-1 flex justify-end">
              <button
                type="button"
                onClick={handleApplyAIRecs}
                className="text-xs font-semibold text-qm-primary hover:text-qm-primary/80 flex items-center gap-1.5 py-1 px-2.5 bg-qm-primary/10 border border-qm-primary/20 rounded-lg transition-colors cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Prefill AI Recommended Department & Team
              </button>
            </div>
          )}
        </div>

        {/* Routing Form */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-qm-text2 mb-1.5">
              Category <span className="text-qm-text2/50 font-normal">(Help Desk verified)</span>
            </label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : '')}
              className="nm-input w-full px-3 py-2 text-sm"
            >
              <option value="">— Select Category —</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Department <span className="text-red-400">*</span>
              </label>
              <select
                value={departmentId}
                onChange={(e) => {
                  const val = e.target.value ? Number(e.target.value) : '';
                  setDepartmentId(val);
                  setTeamId('');
                }}
                className="nm-input w-full px-3 py-2 text-sm"
              >
                <option value="">— Select Department —</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} {d.id === ticket.ai_recommended_department_id ? '(AI Recommended)' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Support Team <span className="text-red-400">*</span>
              </label>
              <select
                value={teamId}
                onChange={(e) => setTeamId(e.target.value ? Number(e.target.value) : '')}
                disabled={!departmentId}
                className="nm-input w-full px-3 py-2 text-sm disabled:opacity-40"
              >
                <option value="">— Select Team —</option>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} {t.id === ticket.ai_recommended_support_team_id ? '(AI Recommended)' : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-qm-text2 mb-1.5">Confirmed Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as TicketPriority)}
                className="nm-input w-full px-3 py-2 text-sm"
              >
                {(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as TicketPriority[]).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Assign to Engineer <span className="text-qm-text2/50 font-normal">(optional — Team Lead will assign)</span>
              </label>
              <select
                value={assignedEngineerId}
                onChange={(e) => setAssignedEngineerId(e.target.value ? Number(e.target.value) : '')}
                disabled={!teamId}
                className="nm-input w-full px-3 py-2 text-sm disabled:opacity-40"
              >
                <option value="">— Team Lead will assign —</option>
                {engineers.map((eng) => (
                  <option key={eng.id} value={eng.id}>
                    {eng.full_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-qm-text2 mb-1.5">
              Routing Note <span className="text-qm-text2/50 font-normal">(optional)</span>
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder="Notes for the team lead / support team..."
              className="nm-input w-full p-2.5 text-sm resize-none"
            />
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-between gap-3 pt-4 border-t border-qm-border flex-wrap">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onEscalate(ticket)}
              className="px-3 py-2 text-xs font-semibold text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-xl transition-colors flex items-center gap-1.5"
            >
              <ArrowUpRight className="w-3.5 h-3.5" />
              Escalate (Critical)
            </button>
            <button
              type="button"
              onClick={() => onRequestClarification(ticket)}
              className="px-3 py-2 text-xs font-semibold text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 rounded-xl transition-colors flex items-center gap-1.5"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              Request Clarification
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="nm-btn-secondary px-4 py-2 text-xs"
            >
              Cancel
            </button>
            <button
              onClick={() =>
                onConfirm({
                  department_id: Number(departmentId),
                  support_team_id: Number(teamId),
                  category_id: categoryId ? Number(categoryId) : null,
                  confirmed_priority: priority,
                  assigned_engineer_id: assignedEngineerId ? Number(assignedEngineerId) : null,
                  note: note.trim() || null,
                })
              }
              disabled={!departmentId || !teamId || loading}
              className={`px-5 py-2 text-xs font-semibold rounded-xl transition-all shadow-md flex items-center gap-1.5 cursor-pointer disabled:opacity-40 ${
                isAIMatch
                  ? 'bg-qm-primary hover:bg-qm-primary/90 text-white shadow-qm-primary/20'
                  : 'bg-qm-cyan hover:bg-qm-cyan/90 text-slate-950 font-bold shadow-qm-cyan/20'
              }`}
            >
              {loading ? (
                'Routing...'
              ) : isAIMatch ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Approve AI Routing
                </>
              ) : (
                'Confirm & Route'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Escalation Modal ─────────────────────────────────────────────────────────
interface EscalateModalProps {
  ticket: Ticket;
  onConfirm: (reason: string, note?: string) => void;
  onClose: () => void;
  loading: boolean;
}

const EscalateModal: React.FC<EscalateModalProps> = ({ ticket, onConfirm, onClose, loading }) => {
  const [reason, setReason] = useState('');
  const [note, setNote] = useState('');

  return (
    <div className="fixed inset-0 nm-overlay flex items-center justify-center z-50 p-4">
      <div className="nm-raised w-full max-w-md p-6 space-y-4 animate-fade-in border border-rose-500/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-rose-400">
            <ShieldAlert className="w-5 h-5" />
            <h3 className="text-base font-bold text-qm-text">Escalate Ticket to CRITICAL</h3>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-qm-raised rounded text-qm-text2">
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-qm-text2">
          Ticket <strong className="text-qm-text">{ticket.ticket_number}</strong>: {ticket.subject}
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-qm-text2 mb-1">
              Escalation Reason <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Active examination disrupted / essential service outage"
              className="nm-input w-full px-3 py-2 text-sm"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-qm-text2 mb-1">
              Internal Note <span className="text-qm-text2/50">(optional)</span>
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder="Additional operational instructions for responders..."
              className="nm-input w-full p-2.5 text-sm resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-qm-border">
          <button onClick={onClose} className="nm-btn-secondary px-4 py-2 text-xs">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(reason.trim(), note.trim() || undefined)}
            disabled={!reason.trim() || loading}
            className="px-4 py-2 text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white rounded-xl disabled:opacity-40 shadow-md shadow-rose-600/20"
          >
            {loading ? 'Escalating...' : 'Confirm Escalation'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Clarification Modal ──────────────────────────────────────────────────────
interface ClarificationModalProps {
  ticket: Ticket;
  onConfirm: (question: string) => void;
  onClose: () => void;
  loading: boolean;
}

const ClarificationModal: React.FC<ClarificationModalProps> = ({ ticket, onConfirm, onClose, loading }) => {
  const [question, setQuestion] = useState('');

  return (
    <div className="fixed inset-0 nm-overlay flex items-center justify-center z-50 p-4">
      <div className="nm-raised w-full max-w-md p-6 space-y-4 animate-fade-in border border-purple-500/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-purple-400">
            <HelpCircle className="w-5 h-5" />
            <h3 className="text-base font-bold text-qm-text">Request User Clarification</h3>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-qm-raised rounded text-qm-text2">
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-qm-text2">
          Ticket <strong className="text-qm-text">{ticket.ticket_number}</strong> will transition to{' '}
          <span className="text-purple-300 font-semibold">Waiting for User</span>.
        </p>

        <div>
          <label className="block text-xs font-semibold text-qm-text2 mb-1">
            Question for Submitter <span className="text-red-400">*</span>
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            placeholder="e.g. Please provide your student roll number and the exact error code appearing on the screen..."
            className="nm-input w-full p-2.5 text-sm resize-none"
            autoFocus
          />
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-qm-border">
          <button onClick={onClose} className="nm-btn-secondary px-4 py-2 text-xs">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(question.trim())}
            disabled={question.trim().length < 5 || loading}
            className="px-4 py-2 text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white rounded-xl disabled:opacity-40 shadow-md shadow-purple-600/20"
          >
            {loading ? 'Sending...' : 'Send Request'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const HelpDeskDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [clusters, setClusters] = useState<IncidentCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'pending' | 'all' | 'incidents'>('pending');
  const [expandedClusterId, setExpandedClusterId] = useState<number | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [routingTicket, setRoutingTicket] = useState<Ticket | null>(null);
  const [escalatingTicket, setEscalatingTicket] = useState<Ticket | null>(null);
  const [clarifyingTicket, setClarifyingTicket] = useState<Ticket | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const loadAll = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      ticketService.listTickets(),
      metadataService.getDepartments(),
      ticketService.listIncidentClusters().catch(() => []),
    ])
      .then(([t, d, c]) => {
        setTickets(t);
        setDepartments(d);
        setClusters(c || []);
      })
      .catch(() => setError('Failed to load data.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const displayed = useMemo(() => {
    return tab === 'pending'
      ? tickets.filter((t) => t.status === 'SUBMITTED' || t.status === 'AWAITING_HELP_DESK_REVIEW')
      : tickets;
  }, [tab, tickets]);

  const filteredTickets = useMemo(() => {
    return filterTickets(displayed, searchQuery);
  }, [displayed, searchQuery]);

  const handleRoute = async (payload: TicketRoutePayload) => {
    if (!routingTicket) return;
    setActionLoading(true);
    try {
      await ticketService.routeTicket(routingTicket.id, payload);
      setRoutingTicket(null);
      loadAll();
    } catch (err: unknown) {
      alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to route ticket.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDirectApproveAI = async (t: Ticket) => {
    if (!t.ai_recommended_department_id || !t.ai_recommended_support_team_id) {
      setRoutingTicket(t);
      return;
    }
    setActionLoading(true);
    try {
      await ticketService.routeTicket(t.id, {
        department_id: t.ai_recommended_department_id,
        support_team_id: t.ai_recommended_support_team_id,
        category_id: t.category_id || null,
        confirmed_priority: t.ai_predicted_priority || t.confirmed_priority || 'MEDIUM',
        note: 'Approved AI routing recommendation',
      });
      loadAll();
    } catch (err: unknown) {
      alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to approve AI recommendation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleEscalateConfirm = async (reason: string, note?: string) => {
    if (!escalatingTicket) return;
    setActionLoading(true);
    try {
      await ticketService.escalateTicket(escalatingTicket.id, { reason, note });
      setEscalatingTicket(null);
      if (routingTicket?.id === escalatingTicket.id) {
        setRoutingTicket(null);
      }
      loadAll();
    } catch (err: unknown) {
      alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to escalate ticket.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleClarificationConfirm = async (question: string) => {
    if (!clarifyingTicket) return;
    setActionLoading(true);
    try {
      await ticketService.requestClarification(clarifyingTicket.id, { question });
      setClarifyingTicket(null);
      if (routingTicket?.id === clarifyingTicket.id) {
        setRoutingTicket(null);
      }
      loadAll();
    } catch (err: unknown) {
      alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to request clarification.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReprocessAll = async () => {
    setReprocessing(true);
    try {
      const res = await ticketService.reprocessAllTriage();
      alert(res.message);
      loadAll();
    } catch {
      alert('Failed to reprocess tickets.');
    } finally {
      setReprocessing(false);
    }
  };

  const getRoutingBadge = (ticket: Ticket) => {
    if (ticket.status === 'APPROVED_FOR_ROUTING' || ticket.status === 'ASSIGNED' || ticket.status === 'IN_PROGRESS' || ticket.status === 'RESOLVED') {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 whitespace-nowrap">
          Routed to Support Team
        </span>
      );
    }
    if (ticket.status === 'WAITING_FOR_USER') {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20 whitespace-nowrap">
          Waiting for User
        </span>
      );
    }
    if (ticket.confirmed_priority === 'CRITICAL' && ticket.ai_priority_explanation?.includes('ESCALATED')) {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/20 whitespace-nowrap">
          Escalated
        </span>
      );
    }
    if (!ticket.ai_recommended_department_id || !ticket.ai_recommended_support_team_id) {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20 whitespace-nowrap">
          Requires Manual Review
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-qm-primary/10 text-qm-primary border border-qm-primary/20 whitespace-nowrap">
        Ready for Routing
      </span>
    );
  };

  const pendingCount = tickets.filter((t) => t.status === 'SUBMITTED' || t.status === 'AWAITING_HELP_DESK_REVIEW').length;
  const routedCount = tickets.filter((t) => t.status === 'APPROVED_FOR_ROUTING' || t.status === 'ASSIGNED').length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {routingTicket && (
        <RouteModal
          ticket={routingTicket}
          departments={departments}
          onConfirm={handleRoute}
          onClose={() => setRoutingTicket(null)}
          onEscalate={(t) => setEscalatingTicket(t)}
          onRequestClarification={(t) => setClarifyingTicket(t)}
          loading={actionLoading}
        />
      )}

      {escalatingTicket && (
        <EscalateModal
          ticket={escalatingTicket}
          onConfirm={handleEscalateConfirm}
          onClose={() => setEscalatingTicket(null)}
          loading={actionLoading}
        />
      )}

      {clarifyingTicket && (
        <ClarificationModal
          ticket={clarifyingTicket}
          onConfirm={handleClarificationConfirm}
          onClose={() => setClarifyingTicket(null)}
          loading={actionLoading}
        />
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs text-qm-text2 uppercase tracking-wider font-semibold mb-1">Help Desk</p>
          <h1 className="text-2xl font-bold text-qm-text">{user?.full_name}</h1>
          <p className="text-sm text-qm-text2 mt-0.5">{user?.organization_name || user?.organization_code} · Incoming Ticket Queue & AI Routing Triage</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Total In Queue', value: tickets.length, color: 'text-qm-text' },
          { label: 'Pending Review', value: pendingCount, color: 'text-qm-warning' },
          { label: 'Routed & Assigned', value: routedCount, color: 'text-qm-cyan' },
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
              {(['pending', 'all', 'incidents'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`nm-tab ${tab === t ? 'nm-tab-active' : ''}`}
                >
                  {t === 'pending' ? 'Pending Review' : t === 'incidents' ? `Incident Groups (${clusters.length})` : 'All Tickets'}
                </button>
              ))}
            </div>
            {tab !== 'incidents' && (
              <TicketSearchBar
                value={searchQuery}
                onChange={setSearchQuery}
                placeholder="Search tickets by ID, subject, keywords..."
                className="max-w-xs"
              />
            )}
            {searchQuery.trim() && tab !== 'incidents' && (
              <span className="text-xs text-qm-text2">({filteredTickets.length} of {displayed.length})</span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleReprocessAll}
              disabled={reprocessing || loading}
              className="flex items-center gap-1.5 text-xs text-qm-primary hover:text-qm-primary/80 font-medium disabled:opacity-40 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {reprocessing ? 'Reprocessing...' : 'Reprocess AI Triage'}
            </button>
            <button onClick={loadAll} className="flex items-center gap-1.5 text-xs text-qm-text2 hover:text-qm-text font-medium transition-colors">
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
        ) : tab === 'incidents' ? (
          <div className="p-4 space-y-3">
            {clusters.length === 0 ? (
              <div className="py-12 text-center text-sm text-qm-text2">
                No incident clusters detected yet. Similar incoming tickets will be automatically grouped here.
              </div>
            ) : (
              clusters.map((c) => {
                const isExpanded = expandedClusterId === c.id;
                const relatedTickets = tickets.filter((t) => c.related_ticket_ids?.includes(t.id));
                return (
                  <div key={c.id} className="border border-qm-border rounded-xl bg-qm-raised/60 overflow-hidden">
                    <div
                      onClick={() => setExpandedClusterId(isExpanded ? null : c.id)}
                      className="p-4 cursor-pointer hover:bg-qm-raised/90 transition-colors flex items-center justify-between gap-4 flex-wrap"
                    >
                      <div className="flex items-center gap-3">
                        <button className="text-qm-text2 hover:text-qm-text">
                          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </button>
                        <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-qm-primary/10 text-qm-primary border border-qm-primary/20">
                          {c.cluster_number}
                        </span>
                        <div>
                          <h4 className="text-sm font-semibold text-qm-text">
                            {c.common_issue_summary || `${c.category || 'Incident'} Cluster`}
                          </h4>
                          <p className="text-xs text-qm-text2 mt-0.5">
                            Category: {c.category || 'General'} · Latest: {formatDate(c.last_reported_at)}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg nm-recessed text-xs text-qm-text2">
                          <Users className="w-3.5 h-3.5 text-qm-primary" />
                          <span>{c.distinct_affected_users} affected users</span>
                          <span className="text-qm-text2/60 font-mono">({c.total_reports} reports)</span>
                        </div>
                        <PriorityBadge priority={c.incident_priority} />
                        <span className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded border ${
                          c.status === 'RESOLVED'
                            ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                            : 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                        }`}>
                          {c.status}
                        </span>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="border-t border-qm-border p-4 bg-qm-bg/40 space-y-3">
                        {c.escalation_reason && (
                          <div className="text-xs px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300">
                            <strong>Escalation Notice:</strong> {c.escalation_reason}
                          </div>
                        )}
                        <div>
                          <h5 className="text-xs font-semibold text-qm-text2 uppercase tracking-wide mb-2">
                            Grouped Tickets in this Incident ({relatedTickets.length})
                          </h5>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {relatedTickets.map((rt) => (
                              <div
                                key={rt.id}
                                onClick={() => navigate(`/tickets/${rt.id}`)}
                                className="p-2.5 rounded-lg border border-qm-border bg-qm-raised/60 hover:bg-qm-raised cursor-pointer transition-colors flex items-center justify-between gap-2"
                              >
                                <div className="min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="font-mono text-xs text-qm-text2">{rt.ticket_number}</span>
                                    <PriorityBadge priority={rt.confirmed_priority ?? rt.impact} />
                                    <StatusBadge status={rt.status} />
                                  </div>
                                  <p className="text-xs text-qm-text truncate mt-1">{rt.subject}</p>
                                  <p className="text-[11px] text-qm-text2 mt-0.5">By {rt.submitted_by_name || 'User'} on {formatDate(rt.created_at)}</p>
                                </div>
                                <Eye className="w-4 h-4 text-qm-text2 flex-shrink-0" />
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        ) : displayed.length === 0 ? (
          <div className="py-12 text-center text-sm text-qm-text2">
            {tab === 'pending' ? 'No tickets pending review.' : 'No tickets found.'}
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
                  {['Ticket #', 'Subject', 'Priority', 'Routing Status', 'AI Recommendation', 'Submitter', 'Created', 'Actions'].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredTickets.map((t) => {
                  const hasAIRecommendation = Boolean(t.ai_recommended_department_id && t.ai_recommended_support_team_id);
                  const isPending = t.status === 'SUBMITTED' || t.status === 'AWAITING_HELP_DESK_REVIEW';

                  return (
                    <tr key={t.id}>
                      <td className="font-mono text-xs text-qm-text2">{t.ticket_number}</td>
                      <td className="font-medium text-qm-text max-w-xs">
                        <span className="line-clamp-1">{t.subject}</span>
                        {t.ai_priority_explanation && (
                          <span className="text-[11px] text-qm-text2/70 block truncate mt-0.5">
                            {t.ai_priority_explanation}
                          </span>
                        )}
                      </td>
                      <td>
                        <PriorityBadge priority={t.confirmed_priority ?? t.ai_predicted_priority ?? t.impact} />
                      </td>
                      <td>
                        <div className="flex flex-col gap-1 items-start">
                          {getRoutingBadge(t)}
                          {t.ai_analysis_status === 'COMPLETED' && (
                            <span className="text-[10px] text-qm-primary/80 font-mono">
                              AI Analysed
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="text-qm-text2 text-xs">
                        {t.ai_recommended_support_team_name ? (
                          <div>
                            <span className="font-medium text-qm-cyan">{t.ai_recommended_support_team_name}</span>
                            <span className="block text-[10px] text-qm-text2/70">{t.ai_recommended_department_name}</span>
                          </div>
                        ) : (
                          <span className="text-qm-text2/60 italic">Needs manual team</span>
                        )}
                      </td>
                      <td className="text-qm-text2">{t.submitted_by_name ?? '—'}</td>
                      <td className="text-qm-text2 whitespace-nowrap">{formatDate(t.created_at)}</td>
                      <td>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {isPending && hasAIRecommendation && (
                            <button
                              onClick={() => handleDirectApproveAI(t)}
                              title="1-Click Approve AI Recommendation & Route to Team"
                              className="px-2.5 py-1 text-xs font-semibold text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-lg border border-emerald-500/20 whitespace-nowrap transition-colors flex items-center gap-1"
                            >
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              Approve & Route
                            </button>
                          )}
                          {isPending && (
                            <button
                              onClick={() => setRoutingTicket(t)}
                              title="Change Recommended Team or Review Details"
                              className="px-2 py-1 text-xs font-semibold text-qm-cyan bg-qm-cyan/10 hover:bg-qm-cyan/20 rounded-lg border border-qm-cyan/20 whitespace-nowrap transition-colors"
                            >
                              {hasAIRecommendation ? 'Change Team' : 'Manual Route'}
                            </button>
                          )}
                          {isPending && (
                            <button
                              onClick={() => setEscalatingTicket(t)}
                              title="Escalate ticket to CRITICAL"
                              className="p-1 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded border border-transparent hover:border-rose-500/20 transition-colors"
                            >
                              <ArrowUpRight className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {isPending && (
                            <button
                              onClick={() => setClarifyingTicket(t)}
                              title="Request clarification from user"
                              className="p-1 text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 rounded border border-transparent hover:border-purple-500/20 transition-colors"
                            >
                              <HelpCircle className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            onClick={() => navigate(`/tickets/${t.id}`)}
                            title="View Full Ticket Details"
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold text-qm-primary bg-qm-primary/10 hover:bg-qm-primary/20 rounded-lg border border-qm-primary/20 transition-colors"
                          >
                            <Eye className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
