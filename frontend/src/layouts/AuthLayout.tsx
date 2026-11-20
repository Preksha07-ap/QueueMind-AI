import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { CinematicBackground } from '../components/ui/CinematicBackground';
import { Sparkles } from 'lucide-react';

/**
 * AuthLayout — Wraps all public/auth routes.
 * Renders the cinematic video background that persists across route navigations.
 * No heavy navbar — just a minimal floating brand.
 */
export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen relative">
      <CinematicBackground />

      {/* Floating brand bar */}
      <header className="relative z-20 w-full">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-qm-primary/20 border border-qm-primary/30 flex items-center justify-center group-hover:bg-qm-primary/30 transition-colors">
              <Sparkles className="w-4 h-4 text-qm-primary" />
            </div>
            <span className="text-lg font-bold text-qm-text tracking-tight">
              QueueMind<span className="text-qm-primary"> AI</span>
            </span>
          </Link>
        </div>
      </header>

      {/* Page content — rendered over the video */}
      <main className="relative z-10 flex-1">
        <Outlet />
      </main>
    </div>
  );
};
