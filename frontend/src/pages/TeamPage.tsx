import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Bare /team is only reached via a stale link — real navigation goes
 * straight to /team/manager or /team/admin. Prefer Manager (the more
 * specific scope) when the user has both, since an admin who is also
 * a store manager most likely wants their own store's view first.
 */
export default function TeamPage() {
  const { user } = useAuth();

  if (user?.storeId) {
    return <Navigate to="/team/manager" replace />;
  }
  return <Navigate to="/team/admin" replace />;
}
