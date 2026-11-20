import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Shield, Lock, Mail, AlertCircle, ArrowRight, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { useAuth, getRoleDashboardPath } from '../../context/AuthContext';
import type { User } from '../../types';

export const PlatformOwnerLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { platformLogin } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const clearError = () => setErrorMessage(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email.trim() || !password) { setErrorMessage('Please provide both email address and password.'); return; }

    setIsSubmitting(true);
    try {
      const authUser: User = await platformLogin({ email: email.trim(), password });
      const destination = getRoleDashboardPath(authUser.role);
      const fromPath = (location.state as { from?: { pathname?: string } })?.from?.pathname;
      const target = fromPath && !fromPath.includes('/login') && !fromPath.includes('/signin') && !fromPath.includes('/platform')
        ? fromPath : destination;
      navigate(target, { replace: true });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMessage(detail || 'Platform authentication failed. Invalid credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-5rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-5 animate-fade-in">
        <button type="button" onClick={() => navigate('/organizer/login')}
          className="flex items-center gap-1.5 text-xs text-qm-text2 hover:text-qm-text transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Organizer Login
        </button>

        <div className="glass-panel p-8 space-y-6 border-qm-secondary/15">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-qm-secondary/15 border border-qm-secondary/25 flex items-center justify-center text-qm-secondary">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-qm-text">Platform Owner</h2>
              <p className="text-xs text-qm-text2 mt-0.5">Global platform administration — authorised access only</p>
            </div>
          </div>

          <div className="p-3 bg-qm-secondary/5 border border-qm-secondary/15 rounded-xl text-xs text-qm-secondary/80 flex items-start gap-2">
            <Shield className="w-4 h-4 text-qm-secondary shrink-0 mt-0.5" />
            <span>This login is restricted to the authorised Platform Owner account only. No organisation code is required.</span>
          </div>

          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-300 leading-relaxed">{errorMessage}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label htmlFor="platformEmail" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Platform Owner Email <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="w-4 h-4 text-qm-text2/50" />
                </div>
                <input id="platformEmail" type="email" value={email}
                  onChange={(e) => { setEmail(e.target.value); clearError(); }}
                  placeholder="owner@queuemind.ai" required autoComplete="email"
                  className="nm-input w-full pl-10 pr-4 py-2.5 text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="platformPassword" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Password <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="w-4 h-4 text-qm-text2/50" />
                </div>
                <input id="platformPassword" type={showPassword ? 'text' : 'password'} value={password}
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
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-qm-secondary/90 to-qm-secondary text-white font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed text-sm shadow-md shadow-qm-secondary/15 hover:shadow-lg hover:shadow-qm-secondary/25"
            >
              {isSubmitting ? <div className="w-4 h-4 nm-spinner" /> : <><span>Sign In as Platform Owner</span><ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>

          <div className="pt-3 border-t border-white/5 text-center">
            <p className="text-xs text-qm-text2/50">
              Organisation staff?{' '}
              <Link to="/organizer/login" className="text-qm-cyan/80 hover:text-qm-cyan transition-colors">Organizer Sign In →</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
