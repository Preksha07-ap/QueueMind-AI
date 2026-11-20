import React from 'react';
import { Search, X } from 'lucide-react';
import type { Ticket } from '../../types';

interface TicketSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export const TicketSearchBar: React.FC<TicketSearchBarProps> = ({
  value,
  onChange,
  placeholder = 'Search tickets by ID, subject, keywords...',
  className = '',
}) => {
  return (
    <div className={`relative flex items-center w-full max-w-sm sm:max-w-md ${className}`}>
      <div className="absolute left-3.5 flex items-center pointer-events-none text-qm-text2/70">
        <Search className="w-4 h-4" />
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="nm-input w-full pl-9 pr-9 py-2 text-xs text-qm-text placeholder:text-qm-text2/50 rounded-xl transition-all focus:ring-1 focus:ring-qm-primary/40 focus:border-qm-primary/50"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          className="absolute right-2.5 p-1 rounded-md text-qm-text2 hover:text-qm-text hover:bg-white/10 transition-colors"
          title="Clear search"
          aria-label="Clear search"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};

/**
 * Filter helper matching ticket ID, subject, keywords in description, category,
 * submitter name/email, and assigned helper/team across all dashboards.
 */
export function filterTickets(tickets: Ticket[], query: string): Ticket[] {
  const q = query.trim().toLowerCase();
  if (!q) return tickets;

  return tickets.filter((t) => {
    // 1. Ticket number & ID
    if (t.ticket_number && t.ticket_number.toLowerCase().includes(q)) return true;
    if (String(t.id).includes(q)) return true;

    // 2. Subject / Title
    if (t.subject && t.subject.toLowerCase().includes(q)) return true;

    // 3. Keywords in description
    if (t.description && t.description.toLowerCase().includes(q)) return true;

    // 4. Category / Subcategory / AI predicted category
    if (t.category_name && t.category_name.toLowerCase().includes(q)) return true;
    if (t.ai_predicted_category && t.ai_predicted_category.toLowerCase().includes(q)) return true;
    if (t.subcategory && t.subcategory.toLowerCase().includes(q)) return true;

    // 5. Submitter name & email
    if (t.submitted_by_name && t.submitted_by_name.toLowerCase().includes(q)) return true;
    if (t.submitted_by_email && t.submitted_by_email.toLowerCase().includes(q)) return true;

    // 6. Assigned engineer, Department, Support team
    if (t.assigned_engineer_name && t.assigned_engineer_name.toLowerCase().includes(q)) return true;
    if (t.department_name && t.department_name.toLowerCase().includes(q)) return true;
    if (t.support_team_name && t.support_team_name.toLowerCase().includes(q)) return true;
    if (t.ai_recommended_department_name && t.ai_recommended_department_name.toLowerCase().includes(q)) return true;
    if (t.ai_recommended_support_team_name && t.ai_recommended_support_team_name.toLowerCase().includes(q)) return true;

    return false;
  });
}
