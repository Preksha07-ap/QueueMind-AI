import { useState, useEffect } from 'react';
import { getHealthStatus } from '../services/healthService';
import type { HealthCheckResponse } from '../types';

export interface HealthState {
  data: HealthCheckResponse | null;
  loading: boolean;
  error: string | null;
}

export const useHealthCheck = () => {
  const [state, setState] = useState<HealthState>({
    data: null,
    loading: true,
    error: null,
  });

  const checkHealth = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const data = await getHealthStatus();
      setState({ data, loading: false, error: null });
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Unable to reach backend API';
      setState({ data: null, loading: false, error: errorMessage });
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return { ...state, refetch: checkHealth };
};
