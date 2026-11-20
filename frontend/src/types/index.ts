export type UserRole =
  | 'USER'
  | 'HELP_DESK'
  | 'SUPPORT_TEAM_MEMBER'
  | 'SUPPORT_TEAM_LEAD'
  | 'ORGANIZATION_ADMIN'
  | 'PLATFORM_OWNER';

export interface User {
  id: number;
  organization_id: number | null;
  organization_name?: string | null;
  organization_code?: string | null;
  full_name: string;
  email: string;
  role: UserRole;
  department_id?: number | null;
  account_status: 'ACTIVE' | 'INACTIVE' | 'SUSPENDED';
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
  org_code?: string;
}

export interface RegisterCredentials {
  org_code: string;
  full_name: string;
  email: string;
  password: string;
}

export interface HealthCheckResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export type TicketPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type TicketStatus =
  | 'SUBMITTED'
  | 'AI_ANALYSIS'
  | 'AWAITING_HELP_DESK_REVIEW'
  | 'APPROVED_FOR_ROUTING'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'WAITING_FOR_USER'
  | 'RESOLVED'
  | 'CLOSED'
  | 'REOPENED';

export interface Ticket {
  id: number;
  organization_id: number;
  ticket_number: string;
  user_id: number;
  submitted_by_name?: string | null;
  submitted_by_email?: string | null;
  category_id?: number | null;
  category_name?: string | null;
  subcategory?: string | null;
  subject: string;
  description: string;
  source: 'WEB' | 'EMAIL' | 'CHAT' | 'PHONE';
  ai_predicted_category?: string | null;
  ai_predicted_priority?: TicketPriority | null;
  ai_priority_score?: number | null;
  ai_priority_explanation?: string | null;
  ai_recommended_department_id?: number | null;
  ai_recommended_department_name?: string | null;
  ai_recommended_support_team_id?: number | null;
  ai_recommended_support_team_name?: string | null;
  ai_duplicate_ticket_id?: number | null;
  ai_duplicate_score?: number | null;
  ai_confidence_score?: number | null;
  ai_analysis_status?: string | null;
  ai_evidence_json?: string | null;
  confirmed_priority?: TicketPriority | null;
  department_id?: number | null;
  department_name?: string | null;
  support_team_id?: number | null;
  support_team_name?: string | null;
  assigned_engineer_id?: number | null;
  assigned_engineer_name?: string | null;
  status: TicketStatus;
  impact?: string | null;
  urgency?: string | null;
  incident_cluster_id?: number | null;
  related_incident_id?: number | null;
  verified_resolution?: string | null;
  is_resolution_verified?: boolean;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  comments_count: number;
  attachments_count: number;
}

export interface IncidentCluster {
  id: number;
  organization_id: number;
  cluster_number: string;
  primary_ticket_id?: number | null;
  common_issue_summary?: string | null;
  category?: string | null;
  incident_priority: TicketPriority;
  status: 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'CLOSED';
  related_ticket_ids: number[];
  distinct_affected_users: number;
  total_reports: number;
  similarity_score?: number | null;
  verified_resolution?: string | null;
  escalation_reason?: string | null;
  is_confirmed: boolean;
  first_reported_at: string;
  last_reported_at: string;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketAttachment {
  id: number;
  organization_id: number;
  ticket_id: number;
  file_name: string;
  file_url: string;
  file_size: number;
  content_type: string | null;
  uploaded_by_user_id: number;
  uploaded_by_name?: string | null;
  created_at: string;
}

export interface TicketComment {
  id: number;
  organization_id: number;
  ticket_id: number;
  user_id: number;
  user_name: string;
  user_role: string;
  comment: string;
  is_internal: boolean;
  created_at: string;
}

export interface TicketHistory {
  id: number;
  organization_id: number;
  ticket_id: number;
  previous_status?: TicketStatus | null;
  new_status: TicketStatus;
  changed_by_user_id?: number | null;
  changed_by_name?: string | null;
  description?: string | null;
  created_at: string;
}

export interface Category {
  id: number;
  organization_id: number;
  name: string;
  description?: string | null;
  department_id?: number | null;
  support_team_id?: number | null;
  is_active: boolean;
}

export interface Department {
  id: number;
  organization_id: number;
  name: string;
  description?: string | null;
  is_active: boolean;
}

export interface SupportTeam {
  id: number;
  organization_id: number;
  department_id: number;
  name: string;
  description?: string | null;
  is_active: boolean;
}

export interface StaffEngineer {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  department_id?: number | null;
  support_team_id?: number | null;
}
