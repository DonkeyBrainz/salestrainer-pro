import { http, HttpResponse } from 'msw';
import type { TokenResponse, LoginResponse, RefreshResponse, User } from '@/types/auth';

// Mock data
export const mockUser: User = {
  userId: '550e8400-e29b-41d4-a716-446655440000',
  email: 'test@example.com',
  name: 'Test User'
};

export const mockTokenResponse: TokenResponse = {
  accessToken: 'mock-access-token',
  refreshToken: 'mock-refresh-token',
  expiresIn: 3600,
  tokenType: 'Bearer',
  user: mockUser
};

export const mockRefreshResponse: RefreshResponse = {
  accessToken: 'mock-refreshed-access-token',
  expiresIn: 3600,
  tokenType: 'Bearer'
};

export const mockLoginResponse: LoginResponse = {
  authUrl: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=test',
  state: 'mock-state-string'
};

// Request handlers
export const handlers = [
  // POST /auth/login
  http.post('/auth/login', async () => {
    return HttpResponse.json(mockLoginResponse);
  }),

  // POST /auth/callback
  http.post('/auth/callback', async ({ request }) => {
    const body = await request.json() as { code: string; state: string };

    if (!body.code || !body.state) {
      return HttpResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: 'Missing code or state' } },
        { status: 400 }
      );
    }

    if (body.state === 'invalid-state') {
      return HttpResponse.json(
        { error: { code: 'UNAUTHORIZED', message: 'Invalid state parameter' } },
        { status: 401 }
      );
    }

    return HttpResponse.json(mockTokenResponse);
  }),

  // POST /auth/refresh
  http.post('/auth/refresh', async ({ request }) => {
    const body = await request.json() as { refreshToken: string };

    if (!body.refreshToken) {
      return HttpResponse.json(
        { error: { code: 'UNAUTHORIZED', message: 'Missing refresh token' } },
        { status: 401 }
      );
    }

    if (body.refreshToken === 'expired-refresh-token') {
      return HttpResponse.json(
        { error: { code: 'UNAUTHORIZED', message: 'Refresh token expired' } },
        { status: 401 }
      );
    }

    return HttpResponse.json(mockRefreshResponse);
  }),

  // POST /auth/logout
  http.post('/auth/logout', async () => {
    return HttpResponse.json({ success: true });
  }),

  // GET /auth/me
  http.get('/auth/me', async ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json(
        { error: { code: 'UNAUTHORIZED', message: 'Missing or invalid token' } },
        { status: 401 }
      );
    }

    return HttpResponse.json(mockUser);
  }),

  // GET /health
  http.get('/health', async () => {
    return HttpResponse.json({
      status: 'healthy',
      version: '1.0.0',
      timestamp: new Date().toISOString()
    });
  })
];
