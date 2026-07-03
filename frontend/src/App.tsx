import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import HomePage from '@/pages/HomePage';
import SessionPage from '@/pages/SessionPage';
import HistoryPage from '@/pages/HistoryPage';
import AdminPage from '@/pages/AdminPage';
import TeamPage from '@/pages/TeamPage';
import ManagerDashboardPage from '@/pages/ManagerDashboardPage';
import AdminDashboardPage from '@/pages/AdminDashboardPage';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/training" element={<SessionPage />} />
      <Route path="/evaluation" element={<SessionPage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/history/:sessionId" element={<HistoryPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route path="/team" element={<TeamPage />} />
      <Route path="/team/manager" element={<ManagerDashboardPage />} />
      <Route path="/team/admin" element={<AdminDashboardPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
