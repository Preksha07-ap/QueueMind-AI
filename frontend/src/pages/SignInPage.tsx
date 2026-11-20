import React from 'react';
import { useNavigate } from 'react-router-dom';
import { UserCircle, Briefcase, ArrowRight, UserPlus } from 'lucide-react';

export const SignInPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-[calc(100vh-5rem)] flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-md space-y-6 animate-fade-in">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-qm-text tracking-tight">Choose Portal</h1>
          <p className="mt-1.5 text-sm text-qm-text2">Select your account type to proceed</p>
        </div>

        <div className="space-y-4">
          {/* USER PATH */}
          <div className="glass-panel p-6 space-y-4 hover:border-qm-primary/30 transition-all">
            <div className="flex items-start gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-qm-primary/15 border border-qm-primary/25 flex items-center justify-center text-qm-primary shrink-0">
                <UserCircle className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h2 className="text-base font-bold text-qm-text">USER</h2>
                <p className="text-xs text-qm-text2 mt-0.5 leading-relaxed">
                  Students, campus members, and employees raising or tracking IT tickets.
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                type="button"
                onClick={() => navigate('/user/login')}
                className="nm-btn-primary w-full py-2.5 px-3 text-xs flex items-center justify-center gap-1.5"
              >
                Sign In <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => navigate('/register')}
                className="nm-btn-secondary w-full py-2.5 px-3 text-xs flex items-center justify-center gap-1.5"
              >
                <UserPlus className="w-3.5 h-3.5 text-qm-primary" /> Register
              </button>
            </div>
          </div>

          {/* ORGANIZER PATH */}
          <div className="glass-panel p-6 space-y-4 hover:border-qm-cyan/30 transition-all">
            <div className="flex items-start gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-qm-cyan/15 border border-qm-cyan/25 flex items-center justify-center text-qm-cyan shrink-0">
                <Briefcase className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h2 className="text-base font-bold text-qm-text">ORGANIZER</h2>
                <p className="text-xs text-qm-text2 mt-0.5 leading-relaxed">
                  Help Desk officers, Solution Helpers, Team Leads, Org Admins, and Platform Owner.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate('/organizer/login')}
              className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-qm-cyan/90 to-qm-cyan text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition-all hover:shadow-lg hover:shadow-qm-cyan/20 cursor-pointer"
            >
              Staff Sign In <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
