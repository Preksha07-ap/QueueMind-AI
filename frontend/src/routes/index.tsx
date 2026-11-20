import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AuthLayout } from '../layouts/AuthLayout';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { LandingPage } from '../pages/LandingPage';
import { SignInPage } from '../pages/SignInPage';
import { UserLoginPage } from '../pages/auth/UserLoginPage';
import { OrganizerLoginPage } from '../pages/auth/OrganizerLoginPage';
import { PlatformOwnerLoginPage } from '../pages/auth/PlatformOwnerLoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';

import { UserDashboard } from '../pages/dashboards/UserDashboard';
import { HelpDeskDashboard } from '../pages/dashboards/HelpDeskDashboard';
import { SupportDashboard } from '../pages/dashboards/SupportDashboard';
import { TeamLeadDashboard } from '../pages/dashboards/TeamLeadDashboard';
import { OrgAdminDashboard } from '../pages/dashboards/OrgAdminDashboard';
import { PlatformOwnerDashboard } from '../pages/dashboards/PlatformOwnerDashboard';

import { NewTicketPage } from '../pages/tickets/NewTicketPage';
import { TicketDetailPage } from '../pages/tickets/TicketDetailPage';

const ALL_ROLES = [
  'USER',
  'HELP_DESK',
  'SUPPORT_TEAM_MEMBER',
  'SUPPORT_TEAM_LEAD',
  'ORGANIZATION_ADMIN',
  'PLATFORM_OWNER',
] as const;

export const router = createBrowserRouter([
  /* ── Public / Auth routes — cinematic video background ─────── */
  {
    element: <AuthLayout />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: 'signin', element: <SignInPage /> },
      { path: 'user/login', element: <UserLoginPage /> },
      { path: 'register', element: <RegisterPage /> },
      { path: 'organizer/login', element: <OrganizerLoginPage /> },
      { path: 'platform/login', element: <PlatformOwnerLoginPage /> },
      { path: 'login', element: <Navigate to="/signin" replace /> },
    ],
  },

  /* ── Authenticated routes — sidebar + top nav layout ───────── */
  {
    element: <DashboardLayout />,
    children: [
      {
        path: 'dashboard/user',
        element: (
          <ProtectedRoute allowedRoles={[...ALL_ROLES]}>
            <UserDashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard/helpdesk',
        element: (
          <ProtectedRoute allowedRoles={['HELP_DESK', 'SUPPORT_TEAM_LEAD', 'ORGANIZATION_ADMIN', 'PLATFORM_OWNER']}>
            <HelpDeskDashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard/support',
        element: (
          <ProtectedRoute allowedRoles={['SUPPORT_TEAM_MEMBER', 'SUPPORT_TEAM_LEAD', 'ORGANIZATION_ADMIN', 'PLATFORM_OWNER']}>
            <SupportDashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard/team-lead',
        element: (
          <ProtectedRoute allowedRoles={['SUPPORT_TEAM_LEAD', 'ORGANIZATION_ADMIN', 'PLATFORM_OWNER']}>
            <TeamLeadDashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard/org-admin',
        element: (
          <ProtectedRoute allowedRoles={['ORGANIZATION_ADMIN', 'PLATFORM_OWNER']}>
            <OrgAdminDashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard/platform-owner',
        element: (
          <ProtectedRoute allowedRoles={['PLATFORM_OWNER']}>
            <PlatformOwnerDashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'tickets/new',
        element: (
          <ProtectedRoute allowedRoles={[...ALL_ROLES]}>
            <NewTicketPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'tickets/:id',
        element: (
          <ProtectedRoute allowedRoles={[...ALL_ROLES]}>
            <TicketDetailPage />
          </ProtectedRoute>
        ),
      },
    ],
  },
]);
