export interface User {
  userId: string;
  email: string;
  name: string;
  createdAt?: string;
  preferences?: UserPreferences;
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
