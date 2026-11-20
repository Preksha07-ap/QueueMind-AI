import React from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth, getRoleDashboardPath } from '../context/AuthContext';
import { useApp } from '../context/AppContext';
import {
  LayoutDashboard, PlusCircle, Building2,
  Shield, LogOut, Menu, X, ChevronRight, Sparkles,
  Headphones, UserCog, Globe,
} from 'lucide-react';
import type { UserRole } from '../types';

interface NavItem {
  label: string;
  path: string;
  icon: React.ElementType;
}

const getNavItems = (role?: UserRole): NavItem[] => {
  switch (role) {
    case 'USER':
      return [
        { label: 'Dashboard', path: '/dashboard/user', icon: LayoutDashboard },
        { label: 'New Ticket', path: '/tickets/new', icon: PlusCircle },
      ];
    case 'HELP_DESK':
      return [
        { label: 'Dashboard', path: '/dashboard/helpdesk', icon: LayoutDashboard },
      ];
    case 'SUPPORT_TEAM_MEMBER':
      return [
        { label: 'Dashboard', path: '/dashboard/support', icon: Headphones },
      ];
    case 'SUPPORT_TEAM_LEAD':
      return [
        { label: 'Dashboard', path: '/dashboard/team-lead', icon: UserCog },
        { label: 'Support Queue', path: '/dashboard/support', icon: Headphones },
      ];
    case 'ORGANIZATION_ADMIN':
      return [
        { label: 'Dashboard', path: '/dashboard/org-admin', icon: Building2 },
        { label: 'Help Desk', path: '/dashboard/helpdesk', icon: LayoutDashboard },
        { label: 'Support Queue', path: '/dashboard/support', icon: Headphones },
      ];
    case 'PLATFORM_OWNER':
      return [
        { label: 'Dashboard', path: '/dashboard/platform-owner', icon: Globe },
        { label: 'Org Admin', path: '/dashboard/org-admin', icon: Building2 },
        { label: 'Help Desk', path: '/dashboard/helpdesk', icon: LayoutDashboard },
        { label: 'Team Lead', path: '/dashboard/team-lead', icon: UserCog },
        { label: 'Support', path: '/dashboard/support', icon: Headphones },
      ];
    default:
      return [{ label: 'Dashboard', path: '/dashboard/user', icon: LayoutDashboard }];
  }
};

const roleLabels: Record<string, string> = {
  USER: 'User',
  HELP_DESK: 'Help Desk',
  SUPPORT_TEAM_MEMBER: 'Solution Helper',
  SUPPORT_TEAM_LEAD: 'Team Lead',
  ORGANIZATION_ADMIN: 'Org Admin',
  PLATFORM_OWNER: 'Platform Owner',
};

export const DashboardLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const { sidebarOpen, setSidebarOpen } = useApp();
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = getNavItems(user?.role);

  const handleSignOut = async () => {
    await logout();
    navigate('/');
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-qm-bg relative flex overflow-x-hidden">
      {/* Subtle background ambient gradients for glass refraction */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-[-10%] left-[-5%] w-[45vw] h-[45vw] rounded-full bg-qm-primary/4 blur-[130px]" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[45vw] h-[45vw] rounded-full bg-qm-secondary/4 blur-[140px]" />
        <div className="absolute top-[40%] right-[15%] w-[35vw] h-[35vw] rounded-full bg-qm-cyan/3 blur-[120px]" />
      </div>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — Glassmorphism left navigation */}
      <aside
        className={`
          fixed top-0 left-0 z-40 h-full w-64 glass-sidebar
          flex flex-col transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static lg:z-auto
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Sidebar header */}
        <div className="h-16 px-5 flex items-center justify-between border-b border-white/10">
          <Link to={getRoleDashboardPath(user?.role)} className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-qm-primary/15 border border-qm-primary/25 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-qm-primary" />
            </div>
            <span className="text-base font-bold text-qm-text tracking-tight">
              QMind<span className="text-qm-primary"> AI</span>
            </span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-qm-text2 hover:text-qm-text transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                  transition-all duration-200
                  ${active
                    ? 'bg-qm-primary/15 text-qm-primary border border-qm-primary/30 shadow-[0_2px_12px_rgba(86,133,255,0.18)]'
                    : 'text-qm-text2 hover:text-qm-text hover:bg-white/5 border border-transparent'
                  }
                `}
              >
                <Icon className="w-4.5 h-4.5 shrink-0" />
                <span>{item.label}</span>
                {active && <ChevronRight className="w-3.5 h-3.5 ml-auto opacity-60" />}
              </Link>
            );
          })}
        </nav>

        {/* Sidebar footer — user info */}
        <div className="border-t border-white/10 p-4 space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-qm-secondary/15 border border-qm-secondary/25 flex items-center justify-center text-qm-secondary text-sm font-bold">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-qm-text truncate">{user?.full_name}</p>
              <p className="text-[11px] text-qm-text2 truncate">
                {roleLabels[user?.role || ''] || user?.role}
              </p>
            </div>
          </div>
          {user?.organization_name && (
            <div className="flex items-center gap-1.5 text-[11px] text-qm-text2 px-1">
              <Building2 className="w-3 h-3 shrink-0" />
              <span className="truncate">{user.organization_name}</span>
            </div>
          )}
          <button
            onClick={handleSignOut}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors border border-transparent hover:border-red-500/20"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 relative z-10">
        {/* Top bar — Glass header */}
        <header className="h-16 glass-header flex items-center justify-between px-4 sm:px-6 sticky top-0 z-20">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-qm-text2 hover:text-qm-text transition-colors p-1"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="hidden lg:flex items-center gap-2 text-sm text-qm-text2">
            {user?.organization_code && (
              <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-xs font-mono text-qm-text2">
                {user.organization_code}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg nm-recessed text-xs">
              <Shield className="w-3.5 h-3.5 text-qm-primary" />
              <span className="text-qm-text font-medium">{user?.full_name?.split(' ')[0]}</span>
              <span className="px-1.5 py-0.5 rounded bg-qm-primary/10 text-qm-primary text-[10px] font-semibold">
                {roleLabels[user?.role || ''] || user?.role}
              </span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
