import type { LoginResponse, TokenResponse, RefreshResponse, User, OAuthProvider } from '@/types/auth';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

class AuthService {
  private static instance: AuthService;

  static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  async login(provider: OAuthProvider = 'google'): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ provider })
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: { message: 'Failed to initiate login' } }));
      throw new Error(error.error?.message || 'Failed to initiate login');
    }

    return response.json();
  }

  async handleCallback(code: string, state: string): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE}/auth/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ code, state })
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: { message: 'Authentication failed' } }));
      throw new Error(error.error?.message || 'Authentication failed');
    }

    return response.json();
  }

  async refresh(refreshToken: string): Promise<RefreshResponse> {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken })
    });

    if (!response.ok) {
      throw new Error('Token refresh failed');
    }

    return response.json();
  }

  async logout(accessToken: string): Promise<void> {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        }
      });
    } catch {
      // Ignore logout errors - we'll clear local state anyway
    }
  }

  async getMe(accessToken: string): Promise<User> {
    const response = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to get user info');
    }

    return response.json();
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const authService = AuthService.getInstance();
