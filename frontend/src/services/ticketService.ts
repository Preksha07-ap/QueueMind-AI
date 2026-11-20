import api from './api';
import type {
  Category,
  Department,
  StaffEngineer,
  SupportTeam,
  Ticket,
  TicketAttachment,
  TicketComment,
  TicketHistory,
  TicketPriority,
  TicketStatus,
} from '../types';

// ── Request Types ──────────────────────────────────────────────────────────────

export interface TicketCreatePayload {
  subject: string;
  description: string;
  category_id?: number | null;
  subcategory?: string | null;
  impact?: string | null;
  urgency?: string | null;
  priority?: TicketPriority;
  source?: 'WEB' | 'EMAIL' | 'CHAT' | 'PHONE';
  attachment_names?: string[];
}

export interface TicketRoutePayload {
  department_id: number;
  support_team_id: number;
  confirmed_priority?: TicketPriority | null;
  category_id?: number | null;
  assigned_engineer_id?: number | null;
  note?: string | null;
}

export interface TicketAssignPayload {
  assigned_engineer_id: number;
  note?: string | null;
}

export interface TicketResolvePayload {
  resolution: string;
}

export interface TicketStatusPayload {
  status: TicketStatus;
  note?: string | null;
}

export interface CommentCreatePayload {
  comment: string;
  is_internal?: boolean;
}

// ── Ticket Service ─────────────────────────────────────────────────────────────

export const ticketService = {
  // --- CRUD ---
  createTicket: async (payload: TicketCreatePayload): Promise<Ticket> => {
    const response = await api.post<Ticket>('/tickets', payload);
    return response.data;
  },

  listTickets: async (params?: {
    status?: TicketStatus;
    priority?: TicketPriority;
    queue?: string;
    search?: string;
    assigned_to_me?: boolean;
  }): Promise<Ticket[]> => {
    const response = await api.get<Ticket[]>('/tickets', { params });
    return response.data;
  },

  getTicket: async (ticketId: number): Promise<Ticket> => {
    const response = await api.get<Ticket>(`/tickets/${ticketId}`);
    return response.data;
  },

  // --- Workflow ---
  routeTicket: async (ticketId: number, payload: TicketRoutePayload): Promise<Ticket> => {
    const response = await api.post<Ticket>(`/tickets/${ticketId}/route`, payload);
    return response.data;
  },

  assignTicket: async (ticketId: number, payload: TicketAssignPayload): Promise<Ticket> => {
    const response = await api.post<Ticket>(`/tickets/${ticketId}/assign`, payload);
    return response.data;
  },

  updateStatus: async (ticketId: number, payload: TicketStatusPayload): Promise<Ticket> => {
    const response = await api.post<Ticket>(`/tickets/${ticketId}/status`, payload);
    return response.data;
  },

  resolveTicket: async (ticketId: number, payload: TicketResolvePayload): Promise<Ticket> => {
    const response = await api.post<Ticket>(`/tickets/${ticketId}/resolve`, payload);
    return response.data;
  },

  escalateTicket: async (ticketId: number, payload: { reason: string; note?: string }): Promise<Ticket> => {
    const response = await api.post<Ticket>(`/tickets/${ticketId}/escalate`, payload);
    return response.data;
  },

  requestClarification: async (ticketId: number, payload: { question: string }): Promise<Ticket> => {
    const response = await api.post<Ticket>(`/tickets/${ticketId}/request-clarification`, payload);
    return response.data;
  },

  reprocessTriage: async (ticketId: number): Promise<Ticket> => {
    const response = await api.post<Ticket>(`/tickets/${ticketId}/reprocess-triage`);
    return response.data;
  },

  reprocessAllTriage: async (): Promise<{ message: string; count: number }> => {
    const response = await api.post<{ message: string; count: number }>('/tickets/reprocess-triage-all');
    return response.data;
  },

  // --- Comments ---
  listComments: async (ticketId: number): Promise<TicketComment[]> => {
    const response = await api.get<TicketComment[]>(`/tickets/${ticketId}/comments`);
    return response.data;
  },

  addComment: async (ticketId: number, payload: CommentCreatePayload): Promise<TicketComment> => {
    const response = await api.post<TicketComment>(`/tickets/${ticketId}/comments`, payload);
    return response.data;
  },

  // --- Attachments ---
  listAttachments: async (ticketId: number): Promise<TicketAttachment[]> => {
    const response = await api.get<TicketAttachment[]>(`/tickets/${ticketId}/attachments`);
    return response.data;
  },

  uploadAttachment: async (ticketId: number, file: File): Promise<TicketAttachment> => {
    const form = new FormData();
    form.append('file', file, file.name);
    const response = await api.post<TicketAttachment>(`/tickets/${ticketId}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // --- History ---
  listHistory: async (ticketId: number): Promise<TicketHistory[]> => {
    const response = await api.get<TicketHistory[]>(`/tickets/${ticketId}/history`);
    return response.data;
  },

  // --- Incident Clusters (Phase 6) ---
  listIncidentClusters: async (params?: { status?: string }): Promise<any[]> => {
    const response = await api.get<any[]>('/incidents', { params });
    return response.data;
  },

  getIncidentCluster: async (clusterId: number): Promise<any> => {
    const response = await api.get<any>(`/incidents/${clusterId}`);
    return response.data;
  },

  confirmIncidentCluster: async (clusterId: number): Promise<any> => {
    const response = await api.post<any>(`/incidents/${clusterId}/confirm`);
    return response.data;
  },

  resolveIncidentCluster: async (clusterId: number, resolution: string): Promise<any> => {
    const response = await api.post<any>(`/incidents/${clusterId}/resolve`, { resolution });
    return response.data;
  },

  getClusterForTicket: async (ticketId: number): Promise<any> => {
    const response = await api.get<any>(`/incidents/ticket/${ticketId}`);
    return response.data;
  },
};

// ── Metadata Service ───────────────────────────────────────────────────────────

export const metadataService = {
  getCategories: async (departmentId?: number): Promise<Category[]> => {
    const params = departmentId ? { department_id: departmentId } : undefined;
    const response = await api.get<Category[]>('/metadata/categories', { params });
    return response.data;
  },

  getDepartments: async (): Promise<Department[]> => {
    const response = await api.get<Department[]>('/metadata/departments');
    return response.data;
  },

  getSupportTeams: async (departmentId?: number): Promise<SupportTeam[]> => {
    const params = departmentId ? { department_id: departmentId } : undefined;
    const response = await api.get<SupportTeam[]>('/metadata/support-teams', { params });
    return response.data;
  },

  getEngineers: async (teamId?: number): Promise<StaffEngineer[]> => {
    const params = teamId ? { team_id: teamId } : undefined;
    const response = await api.get<StaffEngineer[]>('/metadata/engineers', { params });
    return response.data;
  },
};
