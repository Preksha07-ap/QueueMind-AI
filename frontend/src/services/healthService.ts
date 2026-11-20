import api from './api';
import type { HealthCheckResponse } from '../types';

export const getHealthStatus = async (): Promise<HealthCheckResponse> => {
  const response = await api.get<HealthCheckResponse>('/health');
  return response.data;
};
