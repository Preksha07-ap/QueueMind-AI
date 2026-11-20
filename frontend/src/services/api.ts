import axios from 'axios';
import { APP_CONFIG } from '../utils/constants';

const api = axios.create({
  baseURL: APP_CONFIG.apiBaseUrl,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Request interceptor: attach bearer token from storage
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('qm_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: handle token expiry
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // If token expired on a protected route, clean up storage
      if (localStorage.getItem('qm_token') && !window.location.pathname.includes('/login')) {
        localStorage.removeItem('qm_token');
        localStorage.removeItem('qm_user');
      }
    }
    return Promise.reject(error);
  }
);

export default api;
