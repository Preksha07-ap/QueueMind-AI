import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ticketService, metadataService } from '../../services/ticketService';
import type { Category, Ticket } from '../../types';
import { ArrowLeft, Send, CheckCircle2, X, ImagePlus, FileText, UploadCloud } from 'lucide-react';
import { StatusBadge } from '../../components/tickets/StatusBadge';

const MAX_FILES = 5;
const MAX_SIZE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = [
  'image/png', 'image/jpeg', 'image/gif', 'image/webp',
  'application/pdf', 'text/plain',
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileIcon({ type }: { type: string }) {
  if (type.startsWith('image/')) return <ImagePlus className="w-3.5 h-3.5 text-qm-primary" />;
  return <FileText className="w-3.5 h-3.5 text-qm-text2" />;
}

export const NewTicketPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [categories, setCategories] = useState<Category[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState<number | null>(null);

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileErrors, setFileErrors] = useState<string[]>([]);
  const [uploadStatus, setUploadStatus] = useState<Record<number, 'uploading' | 'done' | 'error'>>({});
  const [filePreviews, setFilePreviews] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const urls: Record<string, string> = {};
    selectedFiles.forEach((f) => {
      if (f.type.startsWith('image/')) {
        urls[`${f.name}-${f.size}`] = URL.createObjectURL(f);
      }
    });
    setFilePreviews(urls);
    return () => {
      Object.values(urls).forEach((u) => URL.revokeObjectURL(u));
    };
  }, [selectedFiles]);

  const [submittedTicket, setSubmittedTicket] = useState<Ticket | null>(null);

  useEffect(() => {
    setLoadingCategories(true);
    metadataService
      .getCategories()
      .then(setCategories)
      .catch(() => setCategories([]))
      .finally(() => setLoadingCategories(false));
  }, []);

  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const pastedFiles: File[] = [];
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.indexOf('image') !== -1) {
          const blob = item.getAsFile();
          if (blob) {
            const timeStr = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
            const ext = blob.type === 'image/jpeg' ? 'jpg' : blob.type === 'image/webp' ? 'webp' : 'png';
            const file = new File([blob], `screenshot_${timeStr}.${ext}`, { type: blob.type });
            pastedFiles.push(file);
          }
        }
      }
      if (pastedFiles.length > 0) {
        const errs: string[] = [];
        const toAdd: File[] = [];
        pastedFiles.forEach((f) => {
          if (f.size > MAX_SIZE_BYTES) {
            errs.push(`${f.name}: exceeds the 5 MB limit.`);
            return;
          }
          if (selectedFiles.length + toAdd.length >= MAX_FILES) {
            errs.push(`Maximum ${MAX_FILES} files allowed.`);
            return;
          }
          toAdd.push(f);
        });
        if (errs.length > 0) setFileErrors(errs);
        if (toAdd.length > 0) setSelectedFiles((prev) => [...prev, ...toAdd]);
      }
    };
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [selectedFiles]);

  const handleFilesSelected = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const errs: string[] = [];
    const toAdd: File[] = [];

    Array.from(newFiles).forEach((f) => {
      if (!ALLOWED_TYPES.includes(f.type)) {
        errs.push(`${f.name}: unsupported type. Use PNG, JPG, GIF, WebP, PDF, or TXT.`);
        return;
      }
      if (f.size > MAX_SIZE_BYTES) {
        errs.push(`${f.name}: exceeds the 5 MB limit.`);
        return;
      }
      if (selectedFiles.length + toAdd.length >= MAX_FILES) {
        errs.push(`Maximum ${MAX_FILES} files allowed.`);
        return;
      }
      if (!selectedFiles.some((ex) => ex.name === f.name && ex.size === f.size)) {
        toAdd.push(f);
      }
    });

    setFileErrors(errs);
    setSelectedFiles((prev) => [...prev, ...toAdd]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setUploadStatus((prev) => {
      const next = { ...prev };
      delete next[index];
      return next;
    });
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    handleFilesSelected(e.dataTransfer.files);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!subject.trim()) { setError('Subject is required.'); return; }
    if (!description.trim()) { setError('Description is required.'); return; }

    setSubmitting(true);
    try {
      const ticket = await ticketService.createTicket({
        subject: subject.trim(),
        description: description.trim(),
        category_id: categoryId,
        source: 'WEB',
      });

      if (selectedFiles.length > 0) {
        const statusMap: Record<number, 'uploading' | 'done' | 'error'> = {};
        for (let i = 0; i < selectedFiles.length; i++) {
          statusMap[i] = 'uploading';
          setUploadStatus({ ...statusMap });
          try {
            await ticketService.uploadAttachment(ticket.id, selectedFiles[i]);
            statusMap[i] = 'done';
          } catch {
            statusMap[i] = 'error';
          }
          setUploadStatus({ ...statusMap });
        }
      }

      setSubmittedTicket(ticket);
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to submit ticket. Please check your connection and try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (submittedTicket) {
    const uploadErrors = Object.values(uploadStatus).filter((s) => s === 'error').length;
    return (
      <div className="max-w-xl mx-auto py-16">
        <div className="nm-raised p-8 text-center space-y-6 animate-fade-in">
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto text-emerald-400">
            <CheckCircle2 className="w-9 h-9" />
          </div>

          <div>
            <span className="text-xs font-mono font-bold text-qm-primary uppercase tracking-widest px-2.5 py-1 rounded bg-qm-primary/10 border border-qm-primary/20">
              Ticket #{submittedTicket.ticket_number}
            </span>
            <h1 className="text-2xl font-bold text-qm-text mt-3">Ticket Submitted Successfully</h1>
            <p className="text-sm text-qm-text2 font-medium mt-1">"{submittedTicket.subject}"</p>
          </div>

          <div className="p-4 rounded-xl nm-recessed text-left space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-qm-text2">Current Status:</span>
              <StatusBadge status={submittedTicket.status} />
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-qm-text2">Ticket ID:</span>
              <span className="font-mono text-qm-text">{submittedTicket.ticket_number}</span>
            </div>
            {selectedFiles.length > 0 && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-qm-text2">Attachments:</span>
                <span className={uploadErrors > 0 ? 'text-amber-400' : 'text-emerald-400'}>
                  {selectedFiles.length - uploadErrors}/{selectedFiles.length} uploaded
                  {uploadErrors > 0 && ' (some failed — you can add them from the ticket page)'}
                </span>
              </div>
            )}
            <p className="text-xs text-qm-text2 pt-2 border-t border-qm-border leading-relaxed">
              📍 <strong>Status Notice:</strong> Your ticket has been received and is currently{' '}
              <strong className="text-amber-300">awaiting Help Desk review</strong>.
              Our automated triage system has recorded your incident details and forwarded them to the staff triage queue.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <button
              onClick={() => navigate(`/tickets/${submittedTicket.id}`)}
              className="nm-btn-primary w-full sm:w-auto px-5 py-2.5 text-xs"
            >
              View Ticket Details
            </button>
            <button
              onClick={() => navigate('/dashboard/user')}
              className="nm-btn-secondary w-full sm:w-auto px-5 py-2.5 text-xs"
            >
              Return to My Tickets
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-lg hover:bg-qm-raised text-qm-text2 hover:text-qm-text transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-qm-text">Raise Support Ticket</h1>
          <p className="text-xs text-qm-text2 mt-0.5">
            Submitting as <strong className="text-qm-text">{user?.full_name}</strong> (
            {user?.role?.replace(/_/g, ' ')}) ·{' '}
            {user?.organization_name || user?.organization_code}
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5 nm-card p-6">
        {/* Subject */}
        <div>
          <label className="block text-xs font-semibold text-qm-text2 mb-1.5">
            Subject <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Cannot access campus WiFi in Library 2nd floor"
            className="nm-input w-full px-3 py-2.5 text-sm"
            required
          />
        </div>

        {/* Category */}
        <div>
          <label className="block text-xs font-semibold text-qm-text2 mb-1.5">
            Category <span className="text-qm-text2/50 font-normal">(optional — AI will infer if left blank)</span>
          </label>
          <select
            value={categoryId ?? ''}
            onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : null)}
            className="nm-input w-full px-3 py-2.5 text-sm"
            disabled={loadingCategories}
          >
            <option value="">— Let AI classify automatically —</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-semibold text-qm-text2 mb-1.5">
            Description <span className="text-red-400">*</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={5}
            placeholder="Provide as much detail as possible: what were you doing, what error did you see, which device, etc."
            className="nm-input w-full p-3 text-sm resize-y"
            required
          />
        </div>

        {/* Attachments Dropzone */}
        <div>
          <label className="block text-xs font-semibold text-qm-text2 mb-1.5">
            Attachments & Screenshots <span className="text-qm-text2/50 font-normal">(Max 5 files, 5 MB each)</span>
          </label>

          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className="nm-recessed p-6 text-center cursor-pointer hover:border-qm-primary/40 border border-dashed border-qm-border transition-colors rounded-xl"
          >
            <UploadCloud className="w-8 h-8 text-qm-primary mx-auto mb-2" />
            <p className="text-sm font-medium text-qm-text">Click to upload or drag and drop</p>
            <p className="text-xs text-qm-text2 mt-1">PNG, JPG, GIF, WebP, PDF, or TXT up to 5 MB</p>
            <p className="text-[11px] text-qm-primary/80 mt-1">Tip: You can paste screenshots with Ctrl+V</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ALLOWED_TYPES.join(',')}
              onChange={(e) => handleFilesSelected(e.target.files)}
              className="hidden"
            />
          </div>

          {fileErrors.length > 0 && (
            <div className="mt-2 space-y-1">
              {fileErrors.map((err, i) => (
                <p key={i} className="text-xs text-red-400">{err}</p>
              ))}
            </div>
          )}

          {selectedFiles.length > 0 && (
            <div className="mt-3 space-y-2">
              {selectedFiles.map((file, idx) => {
                const previewKey = `${file.name}-${file.size}`;
                const previewUrl = filePreviews[previewKey];
                return (
                  <div key={idx} className="nm-recessed p-2.5 rounded-lg flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                      {previewUrl ? (
                        <img src={previewUrl} alt={file.name} className="w-8 h-8 rounded object-cover border border-qm-border" />
                      ) : (
                        <FileIcon type={file.type} />
                      )}
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-qm-text truncate">{file.name}</p>
                        <p className="text-[10px] text-qm-text2">{formatBytes(file.size)}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveFile(idx)}
                      className="p-1 hover:bg-qm-raised text-qm-text2 hover:text-red-400 rounded transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="nm-btn-primary w-full py-3 px-4 text-sm flex items-center justify-center gap-2"
        >
          {submitting ? (
            <div className="w-4 h-4 nm-spinner" />
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span>Submit Ticket</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};
