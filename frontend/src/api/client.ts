import type {
  Programme,
  ProgrammeListResponse,
  CreateProgrammeRequest,
  AnalysisResult,
  DiscoveryResult,
  SAPConnectionConfig,
  DataReadinessResult,
  TestForgeResult,
  InfrastructurePlan,
  MigrationPlan,
  CutoverPlan,
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

  // -------------------------------------------------------------------
  // Data Readiness (M03)
  // -------------------------------------------------------------------

  async getDataReadiness(programmeId: string): Promise<DataReadinessResult> {
    return this.request<DataReadinessResult>(
      `/data-readiness/programmes/${programmeId}`,
    );
  }

  async runProfiling(programmeId: string): Promise<DataReadinessResult> {
    return this.request<DataReadinessResult>(
      `/data-readiness/programmes/${programmeId}/profile`,
      { method: 'POST' },
    );
  }

  // -------------------------------------------------------------------
  // TestForge (M04)
  // -------------------------------------------------------------------

  async getTestResults(programmeId: string): Promise<TestForgeResult> {
    return this.request<TestForgeResult>(
      `/test-forge/programmes/${programmeId}`,
    );
  }

  async generateTests(programmeId: string): Promise<TestForgeResult> {
    return this.request<TestForgeResult>(
      `/test-forge/programmes/${programmeId}/generate`,
      { method: 'POST' },
    );
  }

  // -------------------------------------------------------------------
  // Infrastructure (M05)
  // -------------------------------------------------------------------

  async getInfrastructurePlan(programmeId: string): Promise<InfrastructurePlan> {
    return this.request<InfrastructurePlan>(
      `/infrastructure/programmes/${programmeId}`,
    );
  }

  async generateInfrastructurePlan(programmeId: string): Promise<InfrastructurePlan> {
    return this.request<InfrastructurePlan>(
      `/infrastructure/programmes/${programmeId}/generate`,
      { method: 'POST' },
    );
  }

  async downloadTerraform(programmeId: string): Promise<Blob> {
    const url = `${this.baseURL}/infrastructure/programmes/${programmeId}/terraform`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new APIError(response.status, 'Failed to download Terraform files');
    }
    return response.blob();
  }

  // -------------------------------------------------------------------
  // Migration Execution (M06)
  // -------------------------------------------------------------------

  async getMigrationPlan(programmeId: string): Promise<MigrationPlan> {
    return this.request<MigrationPlan>(
      `/migration/programmes/${programmeId}`,
    );
  }

  async createMigrationPlan(programmeId: string): Promise<MigrationPlan> {
    return this.request<MigrationPlan>(
      `/migration/programmes/${programmeId}/plan`,
      { method: 'POST' },
    );
  }

  async executeMigration(programmeId: string): Promise<MigrationPlan> {
    return this.request<MigrationPlan>(
      `/migration/programmes/${programmeId}/execute`,
      { method: 'POST' },
    );
  }

  // -------------------------------------------------------------------
  // Cutover (M07)
  // -------------------------------------------------------------------

  async getCutoverStatus(programmeId: string): Promise<CutoverPlan> {
    return this.request<CutoverPlan>(
      `/cutover/status/${programmeId}`,
    );
  }

  /** @deprecated Use getCutoverStatus instead */
  async getCutoverPlan(programmeId: string): Promise<CutoverPlan> {
    return this.getCutoverStatus(programmeId);
  }

  async generateRunbook(programmeId: string): Promise<CutoverPlan> {
    return this.request<CutoverPlan>(
      `/cutover/runbook/${programmeId}`,
      {
        method: 'POST',
        body: JSON.stringify({
          migration_tasks: [],
          integration_inventory: [],
          data_sequences: [],
        }),
      },
    );
  }

  async startCutover(runbookId: string): Promise<CutoverPlan> {
    return this.request<CutoverPlan>(
      `/cutover/execute/${runbookId}`,
      { method: 'POST' },
    );
  }

  async startHypercare(programmeId: string): Promise<CutoverPlan> {
    return this.request<CutoverPlan>(
      `/cutover/hypercare/${programmeId}`,
      {
        method: 'POST',
        body: JSON.stringify({
          duration_days: 90,
          monitoring_config: {},
        }),
      },
    );
  }

  async updateCutoverTask(
    executionId: string,
    taskId: string,
    taskStatus: string,
    notes?: string,
  ): Promise<CutoverPlan> {
    return this.request<CutoverPlan>(
      `/cutover/task/${executionId}/${taskId}`,
      {
        method: 'PUT',
        body: JSON.stringify({ status: taskStatus, notes }),
      },
    );
  }

  async evaluateGate(
    executionId: string,
    gateId: string,
    checks: Record<string, unknown>,
  ): Promise<unknown> {
    return this.request<unknown>(
      `/cutover/gate/${executionId}/${gateId}`,
      {
        method: 'POST',
        body: JSON.stringify(checks),
      },
    );
  }
}

export const apiClient = new HanaForgeClient();
export { HanaForgeClient, APIError };
