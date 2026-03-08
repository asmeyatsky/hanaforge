import type {
  Programme,
  ProgrammeListResponse,
  CreateProgrammeRequest,
  AnalysisResult,
  DiscoveryResult,
  SAPConnectionConfig,
} from '../types';

class APIError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'APIError';
  }
}

class HanaForgeClient {
  private baseURL: string;

  constructor(baseURL = '/api/v1') {
    this.baseURL = baseURL;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.baseURL}${path}`;
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorBody = await response.text().catch(() => 'Unknown error');
      throw new APIError(response.status, errorBody);
    }

    return response.json() as Promise<T>;
  }

  // -------------------------------------------------------------------
  // Programmes
  // -------------------------------------------------------------------

  async createProgramme(data: CreateProgrammeRequest): Promise<Programme> {
    return this.request<Programme>('/programmes', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listProgrammes(): Promise<ProgrammeListResponse> {
    return this.request<ProgrammeListResponse>('/programmes');
  }

  async getProgramme(id: string): Promise<Programme> {
    return this.request<Programme>(`/programmes/${id}`);
  }

  // -------------------------------------------------------------------
  // Discovery
  // -------------------------------------------------------------------

  async startDiscovery(
    programmeId: string,
    connection: SAPConnectionConfig,
  ): Promise<DiscoveryResult> {
    return this.request<DiscoveryResult>(
      `/programmes/${programmeId}/discovery`,
      {
        method: 'POST',
        body: JSON.stringify(connection),
      },
    );
  }

  // -------------------------------------------------------------------
  // ABAP Analysis
  // -------------------------------------------------------------------

  async uploadABAPSource(
    programmeId: string,
    file: File,
  ): Promise<{ objects_parsed: number }> {
    const formData = new FormData();
    formData.append('file', file);

    return this.request<{ objects_parsed: number }>(
      `/programmes/${programmeId}/abap-source`,
      {
        method: 'POST',
        body: formData,
      },
    );
  }

  async runAnalysis(programmeId: string): Promise<AnalysisResult> {
    return this.request<AnalysisResult>(
      `/programmes/${programmeId}/analysis`,
      { method: 'POST' },
    );
  }

  async getAnalysisResults(programmeId: string): Promise<AnalysisResult> {
    return this.request<AnalysisResult>(
      `/programmes/${programmeId}/analysis`,
    );
  }
}

export const apiClient = new HanaForgeClient();
export { HanaForgeClient, APIError };
