import api from './api';
import type { LoginCredentials, RegisterCredentials, TokenResponse, User } from '../types';

export const authService = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>('/auth/login', credentials);
    return response.data;
  },

  platformLogin: async (credentials: { email: string; password: string }): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>('/auth/platform-login', credentials);
    return response.data;
  },

  register: async (credentials: RegisterCredentials): Promise<User> => {
    const response = await api.post<User>('/auth/register', credentials);
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  logout: async (): Promise<void> => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem('qm_token');
      localStorage.removeItem('qm_user');
    }
  },
};
