import { describe, it, expect, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';
import { setStoredAuth, clearStoredAuth } from '@/test/utils';
import { mockUser, mockTokenResponse } from '@/test/mocks/handlers';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';

// Wrapper for hook tests
function wrapper({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe('AuthContext', () => {
  describe('initial state', () => {
    it('should resolve to not authenticated when no stored auth', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      // After load completes, should not be authenticated (no stored auth)
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('should load stored auth from localStorage', async () => {
      const futureExpiry = Date.now() + 3600 * 1000; // 1 hour from now
      setStoredAuth({
        accessToken: 'stored-token',
        refreshToken: 'stored-refresh',
        expiresAt: futureExpiry,
        user: mockUser
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.accessToken).toBe('stored-token');
    });

    it('should refresh expired token on load', async () => {
      const pastExpiry = Date.now() - 1000; // Already expired
      setStoredAuth({
        accessToken: 'expired-token',
        refreshToken: 'valid-refresh',
        expiresAt: pastExpiry,
        user: mockUser
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.accessToken).toBe('mock-refreshed-access-token');
    });

    it('should logout if refresh fails on load', async () => {
      const pastExpiry = Date.now() - 1000;
      setStoredAuth({
        accessToken: 'expired-token',
        refreshToken: 'expired-refresh-token', // This triggers 401 in mock
        expiresAt: pastExpiry,
        user: mockUser
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });
  });

  describe('login', () => {
    it('should redirect to auth URL', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.login();
      });

      // Check that window.location.href was set
      expect(window.location.href).toContain('google.com');
      // Signed state stashed in first-party sessionStorage for the callback
      expect(sessionStorage.getItem('lsc_oauth_state')).toBe('mock-signed-state');
    });

    it('should set error on login failure', async () => {
      server.use(
        http.post('/auth/login', () => {
          return HttpResponse.json(
            { error: { message: 'Login failed' } },
            { status: 500 }
          );
        })
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.login();
      });

      expect(result.current.error).toBe('Login failed');
    });
  });

  describe('handleCallback', () => {
    it('should authenticate with valid code and state', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.handleCallback('valid-code', 'valid-state');
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.accessToken).toBe(mockTokenResponse.accessToken);

      // Check localStorage was updated
      expect(localStorage.getItem('lsc_access_token')).toBe(mockTokenResponse.accessToken);
      expect(localStorage.getItem('lsc_refresh_token')).toBe(mockTokenResponse.refreshToken);
    });

    it('should set error on invalid callback', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.handleCallback('code', 'invalid-state');
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.error).toBe('Invalid state parameter');
    });
  });

  describe('logout', () => {
    it('should clear auth state and storage', async () => {
      setStoredAuth({
        accessToken: 'token',
        refreshToken: 'refresh',
        expiresAt: Date.now() + 3600000,
        user: mockUser
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.accessToken).toBeNull();

      // Check localStorage was cleared
      expect(localStorage.getItem('lsc_access_token')).toBeNull();
      expect(localStorage.getItem('lsc_refresh_token')).toBeNull();
    });
  });

  describe('getValidToken', () => {
    it('should return token if not expired', async () => {
      const futureExpiry = Date.now() + 3600000;
      setStoredAuth({
        accessToken: 'valid-token',
        refreshToken: 'refresh',
        expiresAt: futureExpiry,
        user: mockUser
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });

      let token: string | null = null;
      await act(async () => {
        token = await result.current.getValidToken();
      });

      expect(token).toBe('valid-token');
    });

    it('should refresh and return new token if near expiry', async () => {
      const nearExpiry = Date.now() + 30000; // 30 seconds - within 1 min buffer
      setStoredAuth({
        accessToken: 'expiring-token',
        refreshToken: 'valid-refresh',
        expiresAt: nearExpiry,
        user: mockUser
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });

      let token: string | null = null;
      await act(async () => {
        token = await result.current.getValidToken();
      });

      expect(token).toBe('mock-refreshed-access-token');
    });
  });

  describe('clearError', () => {
    it('should clear error state', async () => {
      server.use(
        http.post('/auth/login', () => {
          return HttpResponse.json(
            { error: { message: 'Test error' } },
            { status: 500 }
          );
        })
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.login();
      });

      expect(result.current.error).toBe('Test error');

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });
});
