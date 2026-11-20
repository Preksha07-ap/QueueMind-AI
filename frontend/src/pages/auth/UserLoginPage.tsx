import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Building2, Lock, Mail, AlertCircle, CheckCircle, ArrowRight, Sparkles, ArrowLeft, UserCircle, Eye, EyeOff } from 'lucide-react';
import { useAuth, getRoleDashboardPath } from '../../context/AuthContext';

interface LocationState {
  email?: string;
  orgCode?: string;
  successMessage?: string;
  from?: { pathname?: string };
}

export const UserLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const state = (location.state as LocationState) || {};

  const [orgCode, setOrgCode] = useState<string>(state.orgCode || 'JSS-01');
  const [email, setEmail] = useState<string>(state.email || '');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(state.successMessage || null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleStudentQuickFill = (e: React.MouseEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setOrgCode('JSS-01');
    setEmail('student@jss.edu');
    setPassword('UserPass@123');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!orgCode.trim()) { setErrorMessage('Please enter your organisation code.'); return; }
    if (!email.trim() || !password) { setErrorMessage('Please provide both email and password.'); return; }

    setIsSubmitting(true);
    try {
      const user = await login({ email: email.trim(), password, org_code: orgCode.trim() });
      const destination = getRoleDashboardPath(user.role);
      const fromPath = state.from?.pathname;
      const target = fromPath && !fromPath.includes('/login') && !fromPath.includes('/signin') && !fromPath.includes('/register')
        ? fromPath : destination;
      navigate(target, { replace: true });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMessage(detail || 'Invalid organisation code, email, or password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-5rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-5 animate-fade-in">
        <button
          onClick={() => navigate('/signin')}
          className="flex items-center gap-1.5 text-xs text-qm-text2 hover:text-qm-text transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Portal Selection
        </button>

        <div className="glass-panel p-8 space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-qm-primary/15 border border-qm-primary/25 flex items-center justify-center text-qm-primary">
              <UserCircle className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-qm-text">User Sign In</h2>
              <p className="text-xs text-qm-text2 mt-0.5">Students & organisation members portal</p>
            </div>
          </div>

          {successMessage && (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-3">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-emerald-300 leading-relaxed font-medium">{successMessage}</div>
            </div>
          )}

          {errorMessage && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-red-300 leading-relaxed">{errorMessage}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="userOrgCode" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Organisation Code <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Building2 className="w-4 h-4 text-qm-text2/50" />
                </div>
                <input
                  id="userOrgCode" type="text" value={orgCode}
                  onChange={(e) => { setOrgCode(e.target.value); if (successMessage) setSuccessMessage(null); }}
                  placeholder="e.g. JSS-01" required
                  className="nm-input w-full pl-10 pr-4 py-2.5 text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="userEmail" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Email Address <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="w-4 h-4 text-qm-text2/50" />
                </div>
                <input
                  id="userEmail" type="email" value={email}
                  onChange={(e) => { setEmail(e.target.value); if (successMessage) setSuccessMessage(null); }}
                  placeholder="student@jss.edu" required
                  className="nm-input w-full pl-10 pr-4 py-2.5 text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="userPassword" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Password <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="w-4 h-4 text-qm-text2/50" />
                </div>
                <input
                  id="userPassword" type={showPassword ? 'text' : 'password'} value={password}
                  onChange={(e) => { setPassword(e.target.value); if (successMessage) setSuccessMessage(null); }}
                  placeholder="••••••••••••" required
                  className="nm-input w-full pl-10 pr-10 py-2.5 text-sm"
                />
                <button
                  type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-qm-text2/50 hover:text-qm-text2 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={isSubmitting}
              className="nm-btn-primary w-full py-2.5 px-4 text-sm flex items-center justify-center gap-2"
            >
              {isSubmitting ? <div className="w-4 h-4 nm-spinner" /> : <><span>Sign In to User Portal</span><ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>

          <div className="text-center pt-3 border-t border-white/5 space-y-2">
            <p className="text-xs text-qm-text2">
              New student or employee?{' '}
              <Link to="/register" className="text-qm-primary hover:text-qm-primary/80 font-semibold underline underline-offset-2">Create an Account</Link>
            </p>
            <p className="text-xs text-qm-text2/60">
              Authorised staff member?{' '}
              <Link to="/organizer/login" className="text-qm-cyan/80 hover:text-qm-cyan transition-colors">Organizer Sign In →</Link>
            </p>
          </div>

          <div className="pt-3 border-t border-white/5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-qm-text2/50 uppercase tracking-wider mb-2">
              <Sparkles className="w-3 h-3 text-qm-primary" /> Demo User Credentials
            </div>
            <button type="button" onClick={handleStudentQuickFill}
              className="nm-btn-secondary w-full py-2 px-3 text-xs text-left flex items-center justify-between"
            >
              <span>🎓 Student: student@jss.edu</span>
              <span className="text-[10px] text-qm-primary font-mono bg-qm-primary/10 px-1.5 py-0.5 rounded">JSS-01</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
