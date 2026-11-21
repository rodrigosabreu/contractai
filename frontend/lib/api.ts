import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { getCookie, setCookie, deleteCookie } from 'cookies-next';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private client: AxiosInstance;
  private refreshPromise: Promise<string> | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
    });

    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const accessToken = getCookie('access_token');
        if (accessToken && config.headers) {
          config.headers.Authorization = `Bearer ${accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !['/auth/login', '/auth/register'].includes(originalRequest.url || '')) {
          originalRequest._retry = true;

          try {
            const newAccessToken = await this.refreshAccessToken();
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            }
            return this.client(originalRequest);
          } catch (refreshError) {
            this.clearAuth();
            if (typeof window !== 'undefined' && !['/login', '/auth/register'].includes(window.location.pathname)) {
              window.location.href = '/login';
            }
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private async refreshAccessToken(): Promise<string> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = (async () => {
      try {
        const refreshToken = getCookie('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await axios.post(
          `${API_URL}/auth/refresh`,
          { refresh_token: refreshToken },
          { withCredentials: true }
        );

        const { access_token, refresh_token } = response.data;
        setCookie('refresh_token', refresh_token, { path: '/', sameSite: 'lax', secure: process.env.NODE_ENV === 'production' });
        setCookie('access_token', access_token, {
          maxAge: 30 * 60, // 30 minutes
          path: '/',
          sameSite: 'lax',
          secure: process.env.NODE_ENV === 'production',
        });

        return access_token;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  private clearAuth() {
    deleteCookie('access_token');
    deleteCookie('refresh_token');
  }

  // Auth endpoints
  async login(email: string, password: string, rememberMe = false) {
    const response = await this.client.post('/auth/login', { email, password, remember_me: rememberMe });
    const { access_token, refresh_token } = response.data.tokens;
    
    setCookie('access_token', access_token, {
      maxAge: 30 * 60,
      path: '/',
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
    });
    setCookie('refresh_token', refresh_token, {
      maxAge: rememberMe ? 30 * 24 * 60 * 60 : 7 * 24 * 60 * 60,
      path: '/',
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
    });

    return response.data;
  }

  async register(data: { email: string; password: string; full_name: string; organization_name: string; organization_slug: string }) {
    const response = await this.client.post('/auth/register', data);
    const { access_token, refresh_token } = response.data.tokens;
    setCookie('access_token', access_token, { path: '/', sameSite: 'lax', secure: process.env.NODE_ENV === 'production' });
    setCookie('refresh_token', refresh_token, { path: '/', sameSite: 'lax', secure: process.env.NODE_ENV === 'production' });
    return response.data;
  }

  async logout() {
    try { await this.client.post('/auth/logout'); } finally { this.clearAuth(); }
  }

  async getCurrentUser() {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  async updateProfile(data: { full_name?: string }) {
    const response = await this.client.patch('/auth/me', data);
    return response.data;
  }

  async changePassword(data: { current_password: string; new_password: string }) {
    await this.client.post('/auth/password/change', data);
  }

  // Contract endpoints
  async getContracts(params?: { page?: number; page_size?: number; status?: string }) {
    const response = await this.client.get('/contracts', { params: { ...params, status: undefined, status_filter: params?.status || undefined } });
    return { ...response.data, items: response.data.contracts };
  }

  async getContract(id: string) {
    const response = await this.client.get(`/contracts/${id}`);
    return response.data;
  }

  async uploadContract(file: File, data: { title: string; description?: string; source?: string; language?: string }) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', data.title);
    if (data.description) formData.append('description', data.description);
    if (data.source) formData.append('source', data.source);
    if (data.language) formData.append('language', data.language);

    const response = await this.client.post('/contracts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async updateContract(id: string, data: { title?: string; description?: string }) {
    const response = await this.client.patch(`/contracts/${id}`, data);
    return response.data;
  }

  async deleteContract(id: string) {
    await this.client.delete(`/contracts/${id}`);
  }

  // Analysis endpoints
  async createAnalysis(data: { contract_id: string; type?: string; llm_provider?: string; llm_model?: string }) {
    const response = await this.client.post('/analysis', data);
    return response.data;
  }

  async getAnalysis(id: string) {
    const response = await this.client.get(`/analysis/${id}`);
    return response.data;
  }

  async getAnalyses(params?: { page?: number; page_size?: number; contract_id?: string; status_filter?: string }) {
    const response = await this.client.get('/analysis', { params });
    return { ...response.data, items: response.data.analyses };
  }

  async deleteAnalysis(id: string) { await this.client.delete(`/analysis/${id}`); }

  // Reports
  async getOrganizationSummary() {
    const response = await this.client.get('/reports/organization/summary');
    return response.data;
  }

  // Clauses
  async getClauses(params?: { page?: number; page_size?: number; analysis_id?: string; contract_id?: string; risk_level?: string }) {
    const response = await this.client.get('/clauses', { params });
    return response.data;
  }

  async searchClauses(query: string, filters?: Record<string, any>) {
    const response = await this.client.post('/clauses/search', { query, ...filters });
    return response.data;
  }

  // Connectors
  async getConnectors() {
    const response = await this.client.get('/connectors');
    return response.data;
  }

  async createConnector(data: { name: string; type: 'google_drive' | 'onedrive'; config?: Record<string, any>; credentials?: Record<string, any> }) {
    const response = await this.client.post('/connectors', data);
    return response.data;
  }

  async updateConnector(id: string, data: Record<string, any>) { return (await this.client.patch(`/connectors/${id}`, data)).data; }
  async deleteConnector(id: string) { await this.client.delete(`/connectors/${id}`); }

  async syncConnector(id: string, data?: { full_sync?: boolean; folder_id?: string }) {
    const response = await this.client.post(`/connectors/${id}/sync`, data);
    return response.data;
  }

  // Organization
  async getMyOrganization() {
    const response = await this.client.get('/organizations/me');
    return response.data;
  }

  async getOrganizationUsers() {
    const response = await this.client.get('/users');
    return response.data;
  }
}

export const api = new ApiClient();