import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import type { AuthState, User, TokenResponse, OAuthProvider } from '@/types/auth';
import { authService } from '@/services/authService';

// Storage keys
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'lsc_access_token',
  REFRESH_TOKEN: 'lsc_refresh_token',
  EXPIRES_AT: 'lsc_expires_at',
  USER: 'lsc_user'
};

// Actions
type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: { user: User; accessToken: string; refreshToken: string; expiresAt: number } }
  | { type: 'AUTH_FAILURE'; payload: string }
  | { type: 'TOKEN_REFRESHED'; payload: { accessToken: string; expiresAt: number } }
  | { type: 'LOGOUT' }
  | { type: 'CLEAR_ERROR' };

// Reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'AUTH_START':
      return { ...state, isLoading: true, error: null };
    case 'AUTH_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        accessToken: action.payload.accessToken,
        refreshToken: action.payload.refreshToken,
        expiresAt: action.payload.expiresAt,
        isAuthenticated: true,
        isLoading: false,
        error: null
      };
    case 'AUTH_FAILURE':
      return {
        ...state,
        user: null,
        accessToken: null,
        refreshToken: null,
        expiresAt: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload
      };
    case 'TOKEN_REFRESHED':
      return {
        ...state,
        accessToken: action.payload.accessToken,
        expiresAt: action.payload.expiresAt
      };
    case 'LOGOUT':
      return {
        user: null,
        accessToken: null,
        refreshToken: null,
        expiresAt: null,
        isAuthenticated: false,
        isLoading: false,
        error: null
      };
    case 'CLEAR_ERROR':
      return { ...state, error: null };
    default:
      return state;
  }
}

// Initial state
const initialState: AuthState = {
  user: null,
  accessToken: null,
  refreshToken: null,
  expiresAt: null,
  isAuthenticated: false,
  isLoading: true,
  error: null
};

// Context
interface AuthContextValue extends AuthState {
  login: (provider?: OAuthProvider) => Promise<void>;
  handleCallback: (code: string, state: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<string | null>;
  getValidToken: () => Promise<string | null>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Provider
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  const clearStorage = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.EXPIRES_AT);
    localStorage.removeItem(STORAGE_KEYS.USER);
  }, []);

  const saveToStorage = useCallback((data: TokenResponse) => {
    const expiresAt = Date.now() + data.expiresIn * 1000;
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.accessToken);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refreshToken);
    localStorage.setItem(STORAGE_KEYS.EXPIRES_AT, expiresAt.toString());
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user));
    return expiresAt;
  }, []);

  // Load stored auth on mount
  useEffect(() => {
    const loadStoredAuth = async () => {
      try {
        const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
        const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
        const expiresAt = localStorage.getItem(STORAGE_KEYS.EXPIRES_AT);
        const userJson = localStorage.getItem(STORAGE_KEYS.USER);

        if (accessToken && refreshToken && expiresAt && userJson) {
          const user = JSON.parse(userJson) as User;
          const expiry = parseInt(expiresAt, 10);

          // Check if token is expired
          if (Date.now() < expiry - 60 * 1000) {
            // Token still valid (with 1 min buffer)
            dispatch({
              type: 'AUTH_SUCCESS',
              payload: { user, accessToken, refreshToken, expiresAt: expiry }
            });
          } else {
            // Try to refresh
            const response = await authService.refresh(refreshToken);
            const newExpiresAt = Date.now() + response.expiresIn * 1000;

            localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, response.accessToken);
            localStorage.setItem(STORAGE_KEYS.EXPIRES_AT, newExpiresAt.toString());

            dispatch({
              type: 'AUTH_SUCCESS',
              payload: { user, accessToken: response.accessToken, refreshToken, expiresAt: newExpiresAt }
            });
          }
        } else {
          dispatch({ type: 'AUTH_FAILURE', payload: '' });
        }
      } catch {
        clearStorage();
        dispatch({ type: 'AUTH_FAILURE', payload: '' });
      }
    };

    loadStoredAuth();
  }, [clearStorage]);

  // Set up token refresh timer
  useEffect(() => {
    if (!state.expiresAt || !state.refreshToken) return;

    // Refresh 5 minutes before expiry
    const refreshTime = state.expiresAt - Date.now() - 5 * 60 * 1000;
    if (refreshTime <= 0) return;

    const timer = setTimeout(async () => {
      try {
        const response = await authService.refresh(state.refreshToken!);
        const newExpiresAt = Date.now() + response.expiresIn * 1000;

        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, response.accessToken);
        localStorage.setItem(STORAGE_KEYS.EXPIRES_AT, newExpiresAt.toString());

        dispatch({
          type: 'TOKEN_REFRESHED',
          payload: { accessToken: response.accessToken, expiresAt: newExpiresAt }
        });
      } catch {
        // Refresh failed, user will need to re-login
        clearStorage();
        dispatch({ type: 'LOGOUT' });
      }
    }, refreshTime);

    return () => clearTimeout(timer);
  }, [state.expiresAt, state.refreshToken, clearStorage]);

  const login = useCallback(async (provider: OAuthProvider = 'google') => {
    dispatch({ type: 'AUTH_START' });
    try {
      const { authUrl } = await authService.login(provider);
      window.location.href = authUrl;
    } catch (err) {
      dispatch({
        type: 'AUTH_FAILURE',
        payload: err instanceof Error ? err.message : 'Failed to initiate login'
      });
    }
  }, []);

  const handleCallback = useCallback(async (code: string, storedState: string) => {
    dispatch({ type: 'AUTH_START' });
    try {
      const response = await authService.handleCallback(code, storedState);
      const expiresAt = saveToStorage(response);
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: {
          user: response.user,
          accessToken: response.accessToken,
          refreshToken: response.refreshToken,
          expiresAt
        }
      });
    } catch (err) {
      dispatch({
        type: 'AUTH_FAILURE',
        payload: err instanceof Error ? err.message : 'Authentication failed'
      });
    }
  }, [saveToStorage]);

  const logout = useCallback(async () => {
    if (state.accessToken) {
      await authService.logout(state.accessToken);
    }
    clearStorage();
    dispatch({ type: 'LOGOUT' });
  }, [state.accessToken, clearStorage]);

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    if (!state.refreshToken) return null;
    try {
      const response = await authService.refresh(state.refreshToken);
      const newExpiresAt = Date.now() + response.expiresIn * 1000;

      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, response.accessToken);
      localStorage.setItem(STORAGE_KEYS.EXPIRES_AT, newExpiresAt.toString());

      dispatch({
        type: 'TOKEN_REFRESHED',
        payload: { accessToken: response.accessToken, expiresAt: newExpiresAt }
      });

      return response.accessToken;
    } catch {
      clearStorage();
      dispatch({ type: 'LOGOUT' });
      return null;
    }
  }, [state.refreshToken, clearStorage]);

  const getValidToken = useCallback(async (): Promise<string | null> => {
    if (!state.accessToken || !state.expiresAt) return null;

    // If token expires in less than 1 minute, refresh it
    if (Date.now() > state.expiresAt - 60 * 1000) {
      return refreshAccessToken();
    }

    return state.accessToken;
  }, [state.accessToken, state.expiresAt, refreshAccessToken]);

  const clearError = useCallback(() => {
    dispatch({ type: 'CLEAR_ERROR' });
  }, []);

  return (
    <AuthContext.Provider value={{
      ...state,
      login,
      handleCallback,
      logout,
      refreshAccessToken,
      getValidToken,
      clearError
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
