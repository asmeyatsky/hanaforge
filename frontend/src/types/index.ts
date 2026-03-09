// --------------------------------------------------------------------------
// Programme types
// --------------------------------------------------------------------------

export interface ComplexityScore {
  score: number;
  risk_level: string;
  benchmark_percentile: number | null;
}

export interface Programme {
  id: string;
  name: string;
  customer_id: string;
  sap_source_version: string;
  target_version: string;
  status: string;
  complexity_score: ComplexityScore | null;
  created_at: string;
}

export interface ProgrammeListResponse {
  programmes: Programme[];
  total: number;
}

export interface CreateProgrammeRequest {
  name: string;
  customer_id: string;
  sap_source_version: string;
  target_version: string;
  go_live_date?: string | null;
}

// --------------------------------------------------------------------------
// Discovery types
// --------------------------------------------------------------------------

export interface DiscoveryResult {
  programme_id: string;
  landscape_id: string;
  system_id: string;
  custom_object_count: number;
  integration_point_count: number;
  complexity_score: ComplexityScore | null;
  migration_recommendation: MigrationRecommendation | null;
}

export interface MigrationRecommendation {
  approach: string;
  confidence: number;
  reasoning: string;
}

// --------------------------------------------------------------------------
// Analysis types
// --------------------------------------------------------------------------

export interface ABAPObject {
  object_id: string;
  object_name: string;
  object_type: string;
  compatibility_status: string;
  deprecated_apis: string[];
  effort_points: number | null;
  remediation_available: boolean;
}

export interface AnalysisResult {
  programme_id: string;
  total_objects: number;
  compatible_count: number;
  incompatible_count: number;
  needs_review_count: number;
  objects: ABAPObject[];
}

// --------------------------------------------------------------------------
// Connection types
// --------------------------------------------------------------------------

export interface SAPConnectionConfig {
  host: string;
  system_number: string;
  client: string;
  user: string;
  password: string;
}

// --------------------------------------------------------------------------
// M03 - Data Readiness types
// --------------------------------------------------------------------------

export interface DataDomain {
  id: string;
  name: string;
  record_count: number;
  quality_score: number;
  profiling_status: 'pending' | 'running' | 'complete' | 'failed';
  last_profiled_at: string | null;
}

export interface DataQualityIssue {
  id: string;
  domain_id: string;
  domain_name: string;
  field: string;
  issue_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  affected_records: number;
}

export interface DataReadinessResult {
  programme_id: string;
  overall_score: number;
  domains: DataDomain[];
  issues: DataQualityIssue[];
  total_records: number;
  profiled_records: number;
}

// --------------------------------------------------------------------------
// M04 - TestForge types
// --------------------------------------------------------------------------

export interface TestScenario {
  id: string;
  name: string;
  description: string;
  status: 'passed' | 'failed' | 'skipped' | 'pending';
  duration_ms: number | null;
  error_message: string | null;
}

export interface TestSuite {
  id: string;
  name: string;
  module: string;
  pass_count: number;
  fail_count: number;
  skip_count: number;
  total_count: number;
  scenarios: TestScenario[];
  created_at: string;
}

export interface TestForgeResult {
  programme_id: string;
  suites: TestSuite[];
  total_pass: number;
  total_fail: number;
  total_skip: number;
  coverage_percent: number;
  generated_at: string;
}

// --------------------------------------------------------------------------
// M05 - Infrastructure types
// --------------------------------------------------------------------------

export interface InfraResource {
  id: string;
  resource_type: 'vm' | 'network' | 'storage' | 'database' | 'load_balancer';
  name: string;
  spec: string;
  region: string;
  estimated_monthly_cost: number;
}

export interface InfrastructurePlan {
  programme_id: string;
  plan_id: string;
  status: 'draft' | 'approved' | 'provisioned';
  region: string;
  sizing_tier: string;
  estimated_monthly_cost: number;
  resources: InfraResource[];
  terraform_plan: string;
  created_at: string;
}

// --------------------------------------------------------------------------
// M06 - Migration Execution types
// --------------------------------------------------------------------------

export type MigrationTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'blocked';

export interface MigrationTask {
  id: string;
  name: string;
  status: MigrationTaskStatus;
  progress_percent: number;
  depends_on: string[];
  started_at: string | null;
  completed_at: string | null;
}

export interface QualityGate {
  id: string;
  name: string;
  passed: boolean | null;
  checked_at: string | null;
  details: string;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  details: string;
}

export interface MigrationPlan {
  programme_id: string;
  plan_id: string;
  status: 'draft' | 'approved' | 'executing' | 'completed' | 'failed';
  tasks: MigrationTask[];
  quality_gates: QualityGate[];
  audit_log: AuditLogEntry[];
  created_at: string;
}

// --------------------------------------------------------------------------
// M07 - Cutover types
// --------------------------------------------------------------------------

export interface RunbookStep {
  id: string;
  order: number;
  name: string;
  description: string;
  estimated_duration_min: number;
  actual_duration_min: number | null;
  status: 'pending' | 'in_progress' | 'completed' | 'skipped' | 'failed';
  owner: string;
}

export interface GoNoGoGate {
  id: string;
  name: string;
  category: string;
  status: 'go' | 'no_go' | 'pending';
  checked_by: string | null;
  checked_at: string | null;
}

export interface HypercareIncident {
  id: string;
  title: string;
  severity: 'P1' | 'P2' | 'P3' | 'P4';
  status: 'open' | 'investigating' | 'resolved' | 'closed';
  reported_at: string;
  resolved_at: string | null;
  assignee: string;
}

export interface CutoverPlan {
  programme_id: string;
  plan_id: string;
  status: 'planning' | 'ready' | 'executing' | 'cutover_complete' | 'hypercare';
  runbook_steps: RunbookStep[];
  go_no_go_gates: GoNoGoGate[];
  incidents: HypercareIncident[];
  cutover_start: string | null;
  cutover_end: string | null;
  hypercare_start: string | null;
  hypercare_end: string | null;
  created_at: string;
}
