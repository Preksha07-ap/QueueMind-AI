import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from '../components/common/Navbar';

export const RootLayout: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-slate-950 font-sans">
      <Navbar />
      <div className="flex-1 flex flex-col">
        <Outlet />
      </div>
    </div>
  );
};
