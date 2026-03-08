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
