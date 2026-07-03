export type UserRole = 'agent' | 'manager' | 'regional_director';

export interface User {
  userId: string;
  email: string;
  name: string;
  createdAt?: string;
  preferences?: UserPreferences;
  role?: UserRole;
  storeId?: string | null;
  region?: string | null;
}

export interface UserPreferences {
  voiceName: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  theme: 'light' | 'dark';
  notificationsEnabled?: boolean;
}

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  tokenType: string;
  user: User;
}

export interface RefreshResponse {
  accessToken: string;
  expiresIn: number;
  tokenType: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginResponse {
  authUrl: string;
  state: string;
}

export type OAuthProvider = 'google' | 'microsoft';
