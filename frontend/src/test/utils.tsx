import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';

interface WrapperProps {
  children: React.ReactNode;
}

// Wrapper with all providers
function AllProviders({ children }: WrapperProps) {
  return (
    <BrowserRouter>
      <AuthProvider>
        {children}
      </AuthProvider>
    </BrowserRouter>
  );
}

// Wrapper with just router (no auth)
function RouterOnlyWrapper({ children }: WrapperProps) {
  return <BrowserRouter>{children}</BrowserRouter>;
}

// Custom render with all providers
function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Custom render with router only
function renderWithRouter(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: RouterOnlyWrapper, ...options });
}

// Storage helpers for tests - uses the mocked localStorage from setup.ts
export function setStoredAuth(data: {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
  user: { userId: string; email: string; name: string };
}) {
  window.localStorage.setItem('lsc_access_token', data.accessToken);
  window.localStorage.setItem('lsc_refresh_token', data.refreshToken);
  window.localStorage.setItem('lsc_expires_at', data.expiresAt.toString());
  window.localStorage.setItem('lsc_user', JSON.stringify(data.user));
}

export function clearStoredAuth() {
  window.localStorage.removeItem('lsc_access_token');
  window.localStorage.removeItem('lsc_refresh_token');
  window.localStorage.removeItem('lsc_expires_at');
  window.localStorage.removeItem('lsc_user');
}

export * from '@testing-library/react';
export { renderWithProviders, renderWithRouter };
