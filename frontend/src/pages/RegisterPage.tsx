import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Building2, User as UserIcon, Mail, Lock, AlertCircle, CheckCircle, ArrowRight, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [orgCode, setOrgCode] = useState('JSS-01');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!orgCode.trim() || !fullName.trim() || !email.trim() || !password) { setErrorMessage('Please fill in all required fields.'); return; }
    if (password !== confirmPassword) { setErrorMessage('Passwords do not match.'); return; }
    if (password.length < 6) { setErrorMessage('Password must be at least 6 characters.'); return; }

    setIsSubmitting(true);
    try {
      const newUser = await register({ org_code: orgCode.trim(), full_name: fullName.trim(), email: email.trim(), password });
      if ((newUser as unknown as { access_token?: string })?.access_token) {
        navigate('/dashboard/user', { replace: true });
        return;
      }
      navigate('/user/login', {
        state: { email: email.trim(), orgCode: orgCode.trim(), successMessage: 'Account created successfully! Please sign in with your credentials.' },
        replace: true,
      });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMessage(detail || 'Registration failed. Please check your organisation code or contact your administrator.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-5rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-5 animate-fade-in">
        <button onClick={() => navigate('/user/login')}
          className="flex items-center gap-1.5 text-xs text-qm-text2 hover:text-qm-text transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to User Sign In
        </button>

        <div className="glass-panel p-8 space-y-6">
          <div>
            <h2 className="text-xl font-bold text-qm-text">Create User Account</h2>
            <p className="mt-1 text-xs text-qm-text2">Register as a student or organisation member</p>
          </div>

          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-red-300 leading-relaxed">{errorMessage}</div>
            </div>
          )}

          {successMessage && (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-3">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-emerald-300 leading-relaxed">{successMessage}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="regOrgCode" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Organisation Code <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Building2 className="w-4 h-4 text-qm-text2/50" /></div>
                <input id="regOrgCode" type="text" value={orgCode} onChange={(e) => setOrgCode(e.target.value)}
                  placeholder="e.g. JSS-01" required className="nm-input w-full pl-10 pr-4 py-2.5 text-sm" />
              </div>
              <p className="mt-1 text-xs text-qm-text2/50">Provided by your institution administrator</p>
            </div>

            <div>
              <label htmlFor="regFullName" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Full Name <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><UserIcon className="w-4 h-4 text-qm-text2/50" /></div>
                <input id="regFullName" type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
                  placeholder="Rahul Verma" required className="nm-input w-full pl-10 pr-4 py-2.5 text-sm" />
              </div>
            </div>

            <div>
              <label htmlFor="regEmail" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Email Address <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Mail className="w-4 h-4 text-qm-text2/50" /></div>
                <input id="regEmail" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="student@jss.edu" required className="nm-input w-full pl-10 pr-4 py-2.5 text-sm" />
              </div>
            </div>

            <div>
              <label htmlFor="regPassword" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Password <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Lock className="w-4 h-4 text-qm-text2/50" /></div>
                <input id="regPassword" type={showPassword ? 'text' : 'password'} value={password}
                  onChange={(e) => setPassword(e.target.value)} placeholder="Minimum 6 characters" required
                  className="nm-input w-full pl-10 pr-10 py-2.5 text-sm" />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-qm-text2/50 hover:text-qm-text2 transition-colors">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label htmlFor="regConfirmPassword" className="block text-xs font-semibold text-qm-text2 mb-1.5">
                Confirm Password <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Lock className="w-4 h-4 text-qm-text2/50" /></div>
                <input id="regConfirmPassword" type={showPassword ? 'text' : 'password'} value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Repeat password" required
                  className="nm-input w-full pl-10 pr-4 py-2.5 text-sm" />
              </div>
            </div>

            <div className="p-3 nm-recessed text-xs text-qm-text2">
              All self-registered accounts are assigned the standard <strong className="text-qm-text">USER</strong> role. Privileged staff roles are granted exclusively by your organisation administrator.
            </div>

            <button type="submit" disabled={isSubmitting}
              className="nm-btn-primary w-full py-2.5 px-4 text-sm flex items-center justify-center gap-2">
              {isSubmitting ? <div className="w-4 h-4 nm-spinner" /> : <><span>Create Account</span><ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>

          <p className="text-center text-xs text-qm-text2 pt-2 border-t border-white/5">
            Already have an account?{' '}
            <Link to="/user/login" className="text-qm-primary hover:text-qm-primary/80 font-semibold underline underline-offset-2">Sign in as User</Link>
          </p>
        </div>
      </div>
    </div>
  );
};
