import { describe, it, expect } from 'vitest';
import { authService } from './authService';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { mockLoginResponse, mockTokenResponse, mockRefreshResponse, mockUser } from '@/test/mocks/handlers';

describe('authService', () => {
  describe('login', () => {
    it('should return auth URL and state', async () => {
      const result = await authService.login();

      expect(result).toEqual(mockLoginResponse);
      expect(result.authUrl).toContain('google.com');
      expect(result.state).toBeTruthy();
    });

    it('should throw on server error', async () => {
      server.use(
        http.post('/auth/login', () => {
          return HttpResponse.json(
            { error: { message: 'Server error' } },
            { status: 500 }
          );
        })
      );

      await expect(authService.login())
        .rejects.toThrow('Server error');
    });
  });

  describe('handleCallback', () => {
    it('should exchange code for tokens', async () => {
      const result = await authService.handleCallback('valid-code', 'valid-state', 'mock-signed-state');

      expect(result).toEqual(mockTokenResponse);
      expect(result.accessToken).toBeTruthy();
      expect(result.refreshToken).toBeTruthy();
      expect(result.user).toEqual(mockUser);
    });

    it('should send the signed state in the request body', async () => {
      let received: { code: string; state: string; signedState?: string | null } | null = null;
      server.use(
        http.post('/auth/callback', async ({ request }) => {
          received = await request.json() as typeof received;
          return HttpResponse.json(mockTokenResponse);
        })
      );

      await authService.handleCallback('valid-code', 'valid-state', 'mock-signed-state');

      expect(received).toMatchObject({ signedState: 'mock-signed-state' });
    });

    it('should throw on invalid state', async () => {
      await expect(authService.handleCallback('code', 'invalid-state', 'mock-signed-state'))
        .rejects.toThrow('Invalid state parameter');
    });

    it('should throw on missing code', async () => {
      await expect(authService.handleCallback('', 'state', 'mock-signed-state'))
        .rejects.toThrow();
    });
  });

  describe('refresh', () => {
    it('should return new access token', async () => {
      const result = await authService.refresh('valid-refresh-token');

      expect(result).toEqual(mockRefreshResponse);
      expect(result.accessToken).toBeTruthy();
      expect(result.expiresIn).toBeGreaterThan(0);
    });

    it('should throw on expired refresh token', async () => {
      await expect(authService.refresh('expired-refresh-token'))
        .rejects.toThrow('Token refresh failed');
    });
  });

  describe('logout', () => {
    it('should complete without error', async () => {
      // logout should not throw
      await expect(authService.logout('valid-token')).resolves.toBeUndefined();
    });

    it('should not throw on server error', async () => {
      server.use(
        http.post('/auth/logout', () => {
          return HttpResponse.json({}, { status: 500 });
        })
      );

      // logout should swallow errors
      await expect(authService.logout('valid-token')).resolves.toBeUndefined();
    });
  });

  describe('getMe', () => {
    it('should return user info with valid token', async () => {
      const result = await authService.getMe('valid-token');

      expect(result).toEqual(mockUser);
      expect(result.userId).toBeTruthy();
      expect(result.email).toBeTruthy();
    });

    it('should throw on invalid token', async () => {
      server.use(
        http.get('/auth/me', () => {
          return HttpResponse.json(
            { error: { message: 'Unauthorized' } },
            { status: 401 }
          );
        })
      );

      await expect(authService.getMe('invalid-token'))
        .rejects.toThrow('Failed to get user info');
    });
  });

  describe('checkHealth', () => {
    it('should return true when healthy', async () => {
      const result = await authService.checkHealth();
      expect(result).toBe(true);
    });

    it('should return false on error', async () => {
      server.use(
        http.get('/health', () => {
          return HttpResponse.json({}, { status: 503 });
        })
      );

      const result = await authService.checkHealth();
      expect(result).toBe(false);
    });
  });
});
