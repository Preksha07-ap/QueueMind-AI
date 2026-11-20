import React from 'react';
import { Navigate } from 'react-router-dom';

/**
 * Legacy `/login` redirect — routes directly to portal selection `/signin`
 * so users are always presented with their appropriate entry path (User vs Organizer).
 */
export const LoginPage: React.FC = () => {
  return <Navigate to="/signin" replace />;
};
