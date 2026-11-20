import React from 'react';
import { useNavigate } from 'react-router-dom';
import { UserCircle, Briefcase, ArrowRight, Sparkles, Zap, Shield, BarChart3 } from 'lucide-react';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-[calc(100vh-5rem)] flex flex-col items-center justify-center px-4 py-16">
      {/* Hero section */}
      <div className="text-center space-y-6 max-w-2xl animate-fade-in">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-qm-primary/10 border border-qm-primary/20 text-qm-primary text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          AI-Powered IT Service Management
        </div>

        {/* Title */}
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1]">
          <span className="text-qm-text">Queue</span>
          <span className="text-qm-primary">Mind</span>
          <span className="text-qm-text"> AI</span>
        </h1>

        {/* Tagline */}
        <p className="text-lg sm:text-xl text-qm-text2 max-w-lg mx-auto leading-relaxed">
          Intelligent Support. Faster Resolution.
        </p>

        {/* Feature pills */}
        <div className="flex items-center justify-center gap-3 flex-wrap pt-2">
          {[
            { icon: Zap, label: 'Smart Triage' },
            { icon: Shield, label: 'Duplicate Detection' },
            { icon: BarChart3, label: 'Incident Intelligence' },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-qm-text2">
              <Icon className="w-3.5 h-3.5 text-qm-cyan" />
              {label}
            </div>
          ))}
        </div>
      </div>

      {/* Entry cards */}
      <div className="mt-12 w-full max-w-lg grid grid-cols-1 sm:grid-cols-2 gap-5 animate-fade-in" style={{ animationDelay: '0.15s' }}>
        {/* USER card */}
        <button
          onClick={() => navigate('/signin')}
          className="glass-panel p-6 text-left group cursor-pointer hover:border-qm-primary/30 transition-all duration-300"
        >
          <div className="w-12 h-12 rounded-xl bg-qm-primary/15 border border-qm-primary/25 flex items-center justify-center mb-4 group-hover:bg-qm-primary/25 transition-colors">
            <UserCircle className="w-6 h-6 text-qm-primary" />
          </div>
          <h2 className="text-lg font-bold text-qm-text mb-1">User Portal</h2>
          <p className="text-xs text-qm-text2 leading-relaxed mb-4">
            Students & members — raise and track tickets.
          </p>
          <div className="flex items-center gap-1.5 text-sm font-semibold text-qm-primary group-hover:gap-2.5 transition-all">
            Get Started <ArrowRight className="w-4 h-4" />
          </div>
        </button>

        {/* ORGANIZER card */}
        <button
          onClick={() => navigate('/organizer/login')}
          className="glass-panel p-6 text-left group cursor-pointer hover:border-qm-cyan/30 transition-all duration-300"
        >
          <div className="w-12 h-12 rounded-xl bg-qm-cyan/15 border border-qm-cyan/25 flex items-center justify-center mb-4 group-hover:bg-qm-cyan/25 transition-colors">
            <Briefcase className="w-6 h-6 text-qm-cyan" />
          </div>
          <h2 className="text-lg font-bold text-qm-text mb-1">Staff Portal</h2>
          <p className="text-xs text-qm-text2 leading-relaxed mb-4">
            Help Desk, Engineers, Leads & Admins.
          </p>
          <div className="flex items-center gap-1.5 text-sm font-semibold text-qm-cyan group-hover:gap-2.5 transition-all">
            Staff Sign In <ArrowRight className="w-4 h-4" />
          </div>
        </button>
      </div>
    </div>
  );
};
