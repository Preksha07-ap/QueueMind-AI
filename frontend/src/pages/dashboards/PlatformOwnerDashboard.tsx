import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import { Building2, Shield, RefreshCw } from 'lucide-react';

interface OrgItem {
  id: number;
  name: string;
  code: string;
  slug: string;
  org_type: string;
  contact_email: string;
  is_active: boolean;
  created_at: string;
}

export const PlatformOwnerDashboard: React.FC = () => {
  const { user } = useAuth();
  const [orgs, setOrgs] = useState<OrgItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchOrgs = async () => {
    setIsLoading(true);
    try {
      const response = await api.get<OrgItem[]>('/organizations');
      setOrgs(response.data);
    } catch {
      // silent
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchOrgs(); }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <p className="text-xs text-qm-text2 uppercase tracking-wider font-semibold mb-1">Platform Owner</p>
        <h1 className="text-2xl font-bold text-qm-text">{user?.full_name}</h1>
        <p className="text-sm text-qm-text2 mt-0.5">{user?.email} · Global Platform Administration</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="nm-stat">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-qm-text2 uppercase tracking-wide">Tenant Organisations</span>
            <Building2 className="w-4 h-4 text-qm-primary" />
          </div>
          <div className="text-3xl font-extrabold text-qm-text">{orgs.length}</div>
          <p className="mt-1 text-xs text-qm-text2">Registered multi-tenant workspaces</p>
        </div>

        <div className="nm-stat">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-qm-text2 uppercase tracking-wide">Active Tenants</span>
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">
            {orgs.filter((o) => o.is_active).length}
          </div>
          <p className="mt-1 text-xs text-qm-text2">Currently active organisations</p>
        </div>

        <div className="nm-stat">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-qm-text2 uppercase tracking-wide">Isolation</span>
            <Shield className="w-4 h-4 text-qm-secondary" />
          </div>
          <div className="text-sm font-bold text-qm-secondary mt-1">RBAC Active</div>
          <p className="mt-1 text-xs text-qm-text2">Tenant boundary enforced via JWT</p>
        </div>
      </div>

      {/* Org table */}
      <div className="nm-card overflow-hidden">
        <div className="px-5 py-4 border-b border-qm-border flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-qm-text">Registered Tenant Organisations</h3>
            <p className="text-xs text-qm-text2 mt-0.5">All colleges, universities and enterprise workspaces</p>
          </div>
          <button onClick={fetchOrgs} className="p-2 text-qm-text2 hover:text-qm-text rounded-lg hover:bg-qm-raised transition-colors">
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 nm-spinner" />
          </div>
        ) : orgs.length === 0 ? (
          <div className="py-12 text-center text-sm text-qm-text2">No organisations provisioned.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="nm-table">
              <thead>
                <tr>
                  {['Organisation Name', 'Code', 'Slug', 'Type', 'Contact', 'Status'].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orgs.map((o) => (
                  <tr key={o.id}>
                    <td className="font-semibold text-qm-text">{o.name}</td>
                    <td className="font-mono text-xs text-qm-primary font-bold">{o.code}</td>
                    <td className="font-mono text-xs text-qm-text2">{o.slug}</td>
                    <td className="text-qm-text2">{o.org_type}</td>
                    <td className="text-qm-text2">{o.contact_email}</td>
                    <td>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${
                        o.is_active
                          ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                          : 'text-red-400 bg-red-500/10 border-red-500/20'
                      }`}>
                        {o.is_active ? 'Active' : 'Inactive'}
                      </span>
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
