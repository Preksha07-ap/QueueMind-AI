import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Building2, Lock, Mail, AlertCircle, ArrowRight, ArrowLeft, Briefcase, Eye, EyeOff } from 'lucide-react';
import { useAuth, getRoleDashboardPath } from '../../context/AuthContext';
import type { User } from '../../types';

export const OrganizerLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [orgCode, setOrgCode] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const clearError = () => setErrorMessage(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!orgCode.trim()) { setErrorMessage('Organisation code is required.'); return; }
    if (!email.trim() || !password) { setErrorMessage('Please provide both email address and password.'); return; }

    setIsSubmitting(true);
    try {
      const authUser: User = await login({ email: email.trim(), password, org_code: orgCode.trim() });
      const destination = getRoleDashboardPath(authUser.role);
      const fromPath = (location.state as { from?: { pathname?: string } })?.from?.pathname;
      const target = fromPath && !fromPath.includes('/login') && !fromPath.includes('/signin') && !fromPath.includes('/register')
        ? fromPath : destination;
      navigate(target, { replace: true });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMessage(detail || 'Authentication failed. Please verify your organisation code, email address, and password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-5rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-5 animate-fade-in">
        <button type="button" onClick={() => navigate('/signin')}
          className="flex items-center gap-1.5 text-xs text-qm-text2 hover:text-qm-text transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Portal Selection
        </button>

        <div className="glass-panel p-8 space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-qm-cyan/15 border border-qm-cyan/25 flex items-center justify-center text-qm-cyan">
              <Briefcase className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-qm-text">Organizer Sign In</h2>
              <p className="text-xs text-qm-text2 mt-0.5">Authorised staff &amp; departmental workspace</p>
            </div>
          </div>

          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-300 leading-relaxed">{errorMessage}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label htmlFor="orgCode" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Organisation Code <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Building2 className="w-4 h-4 text-qm-text2/50" />
                </div>
                <input id="orgCode" type="text" value={orgCode}
                  onChange={(e) => { setOrgCode(e.target.value); clearError(); }}
                  placeholder="e.g. JSS-01" required autoComplete="organization"
                  className="nm-input w-full pl-10 pr-4 py-2.5 text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="staffEmail" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Staff Email Address <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="w-4 h-4 text-qm-text2/50" />
                </div>
                <input id="staffEmail" type="email" value={email}
                  onChange={(e) => { setEmail(e.target.value); clearError(); }}
                  placeholder="helpdesk@jss.edu" required autoComplete="email"
                  className="nm-input w-full pl-10 pr-4 py-2.5 text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="staffPassword" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Password <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="w-4 h-4 text-qm-text2/50" />
                </div>
                <input id="staffPassword" type={showPassword ? 'text' : 'password'} value={password}
                  onChange={(e) => { setPassword(e.target.value); clearError(); }}
                  placeholder="••••••••••••" required autoComplete="current-password"
                  className="nm-input w-full pl-10 pr-10 py-2.5 text-sm"
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-qm-text2/50 hover:text-qm-text2 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={isSubmitting}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-qm-cyan/90 to-qm-cyan text-white font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed text-sm shadow-md shadow-qm-cyan/15 hover:shadow-lg hover:shadow-qm-cyan/25"
            >
              {isSubmitting ? <div className="w-4 h-4 nm-spinner" /> : <><span>Sign In</span><ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>

          <div className="pt-3 border-t border-white/5 space-y-2 text-center">
            <p className="text-xs text-qm-text2">
              Student or general user?{' '}
              <Link to="/user/login" className="text-qm-primary hover:text-qm-primary/80 font-semibold underline underline-offset-2">User Sign In</Link>
            </p>
            <p className="text-xs text-qm-text2/50">
              Platform administration?{' '}
              <Link to="/platform/login" className="text-qm-secondary/80 hover:text-qm-secondary transition-colors">Platform Owner →</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
