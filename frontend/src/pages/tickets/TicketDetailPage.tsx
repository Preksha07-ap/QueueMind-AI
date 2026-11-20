import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ticketService } from '../../services/ticketService';
import type { Ticket, TicketAttachment, TicketComment, TicketHistory, TicketStatus, IncidentCluster } from '../../types';
import { StatusBadge, PriorityBadge } from '../../components/tickets/StatusBadge';
import { ArrowLeft, Send, ChevronDown, ChevronUp, Lock, X, Sparkles, AlertTriangle, BookOpen, Paperclip, Download, ExternalLink, FileText, Users } from 'lucide-react';

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });

interface ResolveModalProps {
  onConfirm: (resolution: string) => void;
  onClose: () => void;
  loading: boolean;
}

const ResolveModal: React.FC<ResolveModalProps> = ({ onConfirm, onClose, loading }) => {
  const [text, setText] = useState('');
  return (
    <div className="fixed inset-0 nm-overlay flex items-center justify-center z-50 p-4">
      <div className="nm-raised w-full max-w-md p-6 animate-fade-in">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-bold text-qm-text">Mark as Resolved</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-qm-raised rounded-lg text-qm-text2 hover:text-qm-text transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-qm-text2 mb-3">Provide a resolution summary for the user.</p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          placeholder="Describe what was done to resolve this issue..."
          className="nm-input w-full p-3 text-sm resize-y"
        />
        <div className="flex justify-end gap-3 mt-4">
          <button onClick={onClose} className="nm-btn-secondary px-4 py-2 text-xs">Cancel</button>
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

export const TicketDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<TicketComment[]>([]);
  const [history, setHistory] = useState<TicketHistory[]>([]);
  const [attachments, setAttachments] = useState<TicketAttachment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clusterData, setClusterData] = useState<IncidentCluster | null>(null);

  const [commentText, setCommentText] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [submittingComment, setSubmittingComment] = useState(false);
  const [commentError, setCommentError] = useState<string | null>(null);

  const [historyOpen, setHistoryOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [showResolveModal, setShowResolveModal] = useState(false);

  const ticketId = Number(id);

  const isUser = user?.role === 'USER';
  const isEngineer = user?.role === 'SUPPORT_TEAM_MEMBER';
  const isStaff = !isUser;

  const aiEvidence = useMemo(() => {
    if (!ticket?.ai_evidence_json) return null;
    try {
      return JSON.parse(ticket.ai_evidence_json);
    } catch {
      return null;
    }
  }, [ticket?.ai_evidence_json]);

  const load = useCallback(async () => {
    if (!ticketId) return;
    setLoading(true);
    setError(null);
    try {
      const [t, c, h, a] = await Promise.all([
        ticketService.getTicket(ticketId),
        ticketService.listComments(ticketId),
        ticketService.listHistory(ticketId),
        ticketService.listAttachments(ticketId).catch(() => []),
      ]);
      setTicket(t); setComments(c); setHistory(h); setAttachments(a);
      if (t.incident_cluster_id) {
        ticketService.getIncidentCluster(t.incident_cluster_id)
          .then((cl) => setClusterData(cl as IncidentCluster))
          .catch(() => setClusterData(null));
      } else {
        setClusterData(null);
      }
    } catch {
      setError('Failed to load ticket. It may not exist or you may not have access.');
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => { load(); }, [load]);

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    setSubmittingComment(true);
    setCommentError(null);
    try {
      const newComment = await ticketService.addComment(ticketId, { comment: commentText.trim(), is_internal: isInternal });
      setComments((prev) => [...prev, newComment]);
      setCommentText('');
      setIsInternal(false);
    } catch {
      setCommentError('Failed to post comment.');
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleStatusChange = async (status: TicketStatus, note?: string) => {
    setActionLoading(true);
    try {
      const updated = await ticketService.updateStatus(ticketId, { status, note });
      setTicket(updated);
      await load();
    } catch { alert('Failed to update status.'); }
    finally { setActionLoading(false); }
  };

  const handleResolve = async (resolution: string) => {
    if (!resolution.trim()) return;
    setActionLoading(true);
    try {
      const updated = await ticketService.resolveTicket(ticketId, { resolution });
      setTicket(updated);
      setShowResolveModal(false);
      await load();
    } catch { alert('Failed to resolve ticket.'); }
    finally { setActionLoading(false); }
  };

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-8 h-8 nm-spinner" />
    </div>
  );

  if (error || !ticket) return (
    <div className="max-w-2xl mx-auto px-4 py-16 text-center">
      <p className="text-red-400 font-medium">{error || 'Ticket not found.'}</p>
      <button onClick={() => navigate(-1)} className="mt-4 nm-btn-secondary px-4 py-2 text-sm">
        Go Back
      </button>
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      {showResolveModal && <ResolveModal onConfirm={handleResolve} onClose={() => setShowResolveModal(false)} loading={actionLoading} />}

      {/* Back + header */}
      <div className="flex items-start gap-3">
        <button onClick={() => navigate(-1)} className="p-2 rounded-lg hover:bg-qm-raised text-qm-text2 hover:text-qm-text transition-colors mt-0.5 cursor-pointer">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono font-semibold text-qm-primary tracking-widest">{ticket.ticket_number}</span>
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.confirmed_priority ?? ticket.impact} />
          </div>
          <h1 className="text-lg font-bold text-qm-text mt-1">{ticket.subject}</h1>
        </div>
      </div>

      {/* Ticket info card */}
      <div className="nm-card p-5 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          {[
            { label: 'Submitted by', value: ticket.submitted_by_name ?? 'Unknown' },
            { label: 'Category', value: ticket.category_name ?? '—' },
            { label: 'Department', value: ticket.department_name ?? '—' },
            { label: 'Support Team', value: ticket.support_team_name ?? '—' },
            { label: 'Assigned to', value: ticket.assigned_engineer_name ?? '—' },
            { label: 'Created', value: formatDate(ticket.created_at) },
            { label: 'Last Updated', value: formatDate(ticket.updated_at) },
            ...(ticket.resolved_at ? [{ label: 'Resolved', value: formatDate(ticket.resolved_at) }] : []),
          ].map((item) => (
            <div key={item.label}>
              <p className="text-qm-text2/70 font-medium mb-0.5">{item.label}</p>
              <p className="text-qm-text font-semibold">{item.value}</p>
            </div>
          ))}
        </div>

        <div>
          <p className="text-xs font-semibold text-qm-text2 mb-1.5">Description</p>
          <div className="nm-recessed p-3.5 rounded-xl text-sm text-qm-text whitespace-pre-wrap leading-relaxed">
            {ticket.description}
          </div>
        </div>

        {/* Attachments & Screenshots */}
        {attachments.length > 0 && (
          <div className="pt-3 border-t border-qm-border">
            <p className="text-xs font-semibold text-qm-text2 mb-2.5 flex items-center gap-1.5">
              <Paperclip className="w-3.5 h-3.5 text-qm-primary" />
              Attachments & Screenshots ({attachments.length})
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {attachments.map((att) => {
                const isImg = att.content_type?.startsWith('image/') || /\.(png|jpg|jpeg|webp|gif)$/i.test(att.file_name);
                return (
                  <div key={att.id} className="nm-recessed p-2.5 rounded-xl border border-qm-border hover:border-qm-primary/30 transition-all flex flex-col gap-2">
                    {isImg ? (
                      <a href={att.file_url} target="_blank" rel="noopener noreferrer" className="block relative group overflow-hidden rounded-lg bg-qm-bg border border-qm-border aspect-video">
                        <img src={att.file_url} alt={att.file_name} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1 text-white text-xs font-medium">
                          <ExternalLink className="w-3.5 h-3.5" /> View Full
                        </div>
                      </a>
                    ) : (
                      <div className="p-3 rounded-lg bg-qm-bg border border-qm-border flex items-center justify-center text-qm-text2 aspect-video">
                        <FileText className="w-8 h-8" />
                      </div>
                    )}
                    <div className="flex items-center justify-between text-xs">
                      <div className="truncate mr-2" title={att.file_name}>
                        <p className="font-medium text-qm-text truncate">{att.file_name}</p>
                        <p className="text-[10px] text-qm-text2">{(att.file_size / 1024).toFixed(1)} KB</p>
                      </div>
                      <a
                        href={att.file_url}
                        download={att.file_name}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-lg bg-qm-raised hover:bg-qm-card text-qm-text2 hover:text-qm-text transition-colors shrink-0"
                        title="Download / View"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-qm-border">
          {isUser && ticket.status === 'RESOLVED' && (
            <button onClick={() => handleStatusChange('CLOSED', 'User confirmed resolution.')} disabled={actionLoading}
              className="px-4 py-2 text-xs font-semibold nm-btn-secondary text-qm-text disabled:opacity-40 transition-colors">
              {actionLoading ? 'Processing...' : 'Close Ticket'}
            </button>
          )}
          {isUser && ticket.status === 'CLOSED' && (
            <button onClick={() => handleStatusChange('REOPENED', 'User reopened the ticket.')} disabled={actionLoading}
              className="px-4 py-2 text-xs font-semibold bg-red-500/10 hover:bg-red-500/20 text-red-300 rounded-xl border border-red-500/20 disabled:opacity-40 transition-colors">
              {actionLoading ? 'Processing...' : 'Reopen Ticket'}
            </button>
          )}
          {isEngineer && ticket.status === 'ASSIGNED' && (
            <button onClick={() => handleStatusChange('IN_PROGRESS', 'Engineer started working.')} disabled={actionLoading}
              className="px-4 py-2 text-xs font-semibold bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 rounded-xl border border-amber-500/20 disabled:opacity-40 transition-colors">
              {actionLoading ? 'Processing...' : 'Start Working'}
            </button>
          )}
          {isEngineer && ticket.status === 'IN_PROGRESS' && (
            <>
              <button onClick={() => handleStatusChange('WAITING_FOR_USER', 'Waiting for user information.')} disabled={actionLoading}
                className="px-4 py-2 text-xs font-semibold nm-btn-secondary disabled:opacity-40 transition-colors">
                Waiting for User
              </button>
              <button onClick={() => setShowResolveModal(true)} disabled={actionLoading}
                className="px-4 py-2 text-xs font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 rounded-xl border border-emerald-500/20 disabled:opacity-40 transition-colors">
                Resolve
              </button>
            </>
          )}
        </div>
      </div>

      {/* Incident Cluster Panel — shown when ticket belongs to a cluster */}
      {isStaff && clusterData && (
        <div className="nm-card p-5 space-y-3.5 border-rose-500/30">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-rose-400" />
            <h2 className="text-xs font-bold text-rose-300 uppercase tracking-wider">Incident Cluster</h2>
            <span className="ml-auto text-xs font-mono text-qm-text2">{clusterData.cluster_number}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="nm-recessed p-2.5 rounded-lg">
              <p className="text-qm-text2 font-medium mb-0.5">Distinct Users Affected</p>
              <p className="text-rose-300 font-bold text-base">{clusterData.distinct_affected_users}</p>
            </div>
            <div className="nm-recessed p-2.5 rounded-lg">
              <p className="text-qm-text2 font-medium mb-0.5">Total Reports</p>
              <p className="text-qm-text font-semibold">{clusterData.total_reports}</p>
            </div>
            <div className="nm-recessed p-2.5 rounded-lg">
              <p className="text-qm-text2 font-medium mb-0.5">Cluster Priority</p>
              <p className={`font-mono font-bold ${clusterData.incident_priority === 'CRITICAL' ? 'text-red-400' :
                  clusterData.incident_priority === 'HIGH' ? 'text-amber-400' :
                    clusterData.incident_priority === 'MEDIUM' ? 'text-yellow-400' : 'text-slate-400'
                }`}>{clusterData.incident_priority}</p>
            </div>
            <div className="nm-recessed p-2.5 rounded-lg">
              <p className="text-qm-text2 font-medium mb-0.5">Status</p>
              <p className="text-qm-text font-semibold capitalize">{clusterData.status}</p>
            </div>
          </div>
          {clusterData.common_issue_summary && (
            <p className="text-xs text-qm-text2 nm-recessed p-2.5 rounded-lg">
              <strong className="text-qm-text">Common Issue:</strong> {clusterData.common_issue_summary}
            </p>
          )}
          {clusterData.escalation_reason && (
            <div className="flex items-start gap-2 bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-lg text-xs text-rose-200">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Escalation Reason</p>
                <p className="text-rose-300/80 text-[11px] mt-0.5">{clusterData.escalation_reason}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Staff-only AI Triage Panel */}
      {isStaff && ticket.ai_analysis_status && (
        <div className="nm-card p-5 space-y-3.5 border-qm-primary/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-qm-primary" />
              <h2 className="text-xs font-bold text-qm-primary uppercase tracking-wider">AI Intake & Triage Analysis</h2>
            </div>
            <span className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded border ${ticket.ai_analysis_status === 'COMPLETED'
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                : ticket.ai_analysis_status === 'FAILED'
                  ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                  : 'bg-amber-500/10 text-amber-300 border-amber-500/20'
              }`}>
              {ticket.ai_analysis_status}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="nm-recessed p-2.5 rounded-lg">
              <p className="text-qm-text2 font-medium mb-0.5">Classification</p>
              <p className="text-qm-text font-semibold">{aiEvidence?.classification?.predicted_category || ticket.category_name || 'General'}</p>
              {ticket.ai_confidence_score !== null && ticket.ai_confidence_score !== undefined && (
                <span className="text-[10px] text-qm-primary font-mono">{Math.round(ticket.ai_confidence_score * 100)}% confidence</span>
              )}
            </div>
            <div className="nm-recessed p-2.5 rounded-lg">
              <p className="text-qm-text2 font-medium mb-0.5">Calculated Priority</p>
              <p className="text-amber-300 font-mono font-semibold">{ticket.confirmed_priority ?? 'MEDIUM'}</p>
              {aiEvidence?.priority?.score !== undefined && (
                <span className="text-[10px] text-qm-text2 font-mono">score: {aiEvidence.priority.score}</span>
              )}
            </div>
            <div className="nm-recessed p-2.5 rounded-lg">
              <p className="text-qm-text2 font-medium mb-0.5">Recommended Dept</p>
              <p className="text-qm-text font-semibold truncate">{ticket.ai_recommended_department_name || (ticket.ai_recommended_department_id ? `Dept #${ticket.ai_recommended_department_id}` : '—')}</p>
            </div>
            <div className="nm-recessed p-2.5 rounded-lg">
              <p className="text-qm-text2 font-medium mb-0.5">Recommended Team</p>
              <p className="text-qm-text font-semibold truncate">{ticket.ai_recommended_support_team_name || (ticket.ai_recommended_support_team_id ? `Team #${ticket.ai_recommended_support_team_id}` : '—')}</p>
            </div>
          </div>

          {aiEvidence?.priority?.reason && (
            <p className="text-xs text-qm-text2 nm-recessed p-2.5 rounded-lg">
              <strong className="text-qm-text">Priority Engine SLA Rule:</strong> {aiEvidence.priority.reason}
            </p>
          )}

          {ticket.ai_duplicate_ticket_id && (
            <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-lg text-xs text-amber-200">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Semantic Duplicate Match</p>
                <p className="text-amber-300/80 text-[11px] mt-0.5">
                  High similarity ({Math.round((ticket.ai_duplicate_score || 0) * 100)}%) with Ticket #{ticket.ai_duplicate_ticket_id}.
                </p>
              </div>
            </div>
          )}

          {aiEvidence?.rag?.matches && aiEvidence.rag.matches.length > 0 && (
            <div className="nm-recessed p-3 rounded-lg space-y-2">
              <div className="flex items-center gap-1.5 text-xs text-qm-primary font-semibold">
                <BookOpen className="w-3.5 h-3.5 text-qm-primary" />
                <span>Knowledge Base Suggestions (RAG)</span>
              </div>
              <div className="space-y-1.5">
                {aiEvidence.rag.matches.map((m: { title?: string; resolution?: string; score?: number }, idx: number) => (
                  <div key={idx} className="text-xs text-qm-text border-l-2 border-qm-primary pl-2 py-0.5">
                    <span className="font-semibold text-qm-text">{m.title}</span>
                    <p className="text-qm-text2 text-[11px] mt-0.5">{m.resolution}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Comments */}
      <div className="nm-card overflow-hidden">
        <div className="px-5 py-4 border-b border-qm-border">
          <h2 className="text-sm font-semibold text-qm-text">Comments ({comments.length})</h2>
        </div>
        <div className="divide-y divide-qm-border">
          {comments.length === 0 ? (
            <p className="px-5 py-6 text-xs text-qm-text2 text-center">No comments yet.</p>
          ) : comments.map((c) => (
            <div key={c.id} className={`px-5 py-4 ${c.is_internal ? 'bg-amber-500/5' : ''}`}>
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="text-xs font-semibold text-qm-text">{c.user_name}</span>
                <span className="text-xs text-qm-text2">{c.user_role.replace(/_/g, ' ')}</span>
                {c.is_internal && (
                  <span className="inline-flex items-center gap-1 text-xs bg-amber-500/10 text-amber-300 border border-amber-500/20 px-1.5 py-0.5 rounded font-semibold">
                    <Lock className="w-3 h-3" /> Internal
                  </span>
                )}
                <span className="ml-auto text-xs text-qm-text2">{formatDate(c.created_at)}</span>
              </div>
              <p className="text-sm text-qm-text whitespace-pre-wrap">{c.comment}</p>
            </div>
          ))}
        </div>

        {/* Comment form */}
        <div className="px-5 py-4 bg-qm-bg/40 border-t border-qm-border">
          <form onSubmit={handleAddComment} className="space-y-3">
            <textarea
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              rows={3}
              placeholder="Write a comment..."
              className="nm-input w-full p-3 text-sm resize-y"
            />
            {commentError && <p className="text-xs text-red-400">{commentError}</p>}
            <div className="flex items-center justify-between">
              {isStaff ? (
                <label className="flex items-center gap-2 text-xs text-qm-text2 cursor-pointer select-none">
                  <input type="checkbox" checked={isInternal} onChange={(e) => setIsInternal(e.target.checked)}
                    className="rounded border-qm-border bg-qm-raised text-amber-500" />
                  <Lock className="w-3 h-3 text-amber-500" />
                  Internal note (staff only)
                </label>
              ) : <span />}
              <button type="submit" disabled={!commentText.trim() || submittingComment}
                className="nm-btn-primary inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold">
                <Send className="w-3.5 h-3.5" />
                {submittingComment ? 'Posting...' : 'Post Comment'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* History */}
      <div className="nm-card overflow-hidden">
        <button onClick={() => setHistoryOpen((v) => !v)}
          className="w-full flex items-center justify-between px-5 py-4 text-sm font-semibold text-qm-text hover:bg-qm-raised/40 transition-colors">
          <span>Status History ({history.length})</span>
          {historyOpen ? <ChevronUp className="w-4 h-4 text-qm-text2" /> : <ChevronDown className="w-4 h-4 text-qm-text2" />}
        </button>
        {historyOpen && (
          <div className="border-t border-qm-border divide-y divide-qm-border">
            {history.length === 0 ? (
              <p className="px-5 py-5 text-xs text-qm-text2 text-center">No history entries.</p>
            ) : history.map((h) => (
              <div key={h.id} className="px-5 py-3 flex items-start gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {h.previous_status && <><StatusBadge status={h.previous_status} /><span className="text-qm-text2 text-xs">→</span></>}
                    <StatusBadge status={h.new_status} />
                  </div>
                  {h.description && <p className="text-xs text-qm-text2 mt-1">{h.description}</p>}
                </div>
                <div className="text-xs text-qm-text2 text-right whitespace-nowrap">
                  <div>{h.changed_by_name ?? 'System'}</div>
                  <div>{formatDate(h.created_at)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
