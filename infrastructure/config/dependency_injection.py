"""Dependency injection container — composition root for HanaForge.

Wires all infrastructure adapters to domain ports and creates use cases
with their dependencies injected.  This is the single place where concrete
implementations are chosen.
"""

from __future__ import annotations

from typing import Any

from application.commands.approve_runbook import ApproveRunbookUseCase
from application.commands.assess_bp_consolidation import AssessBPConsolidationUseCase
from application.commands.assess_universal_journal import AssessUniversalJournalUseCase
from application.commands.create_infrastructure_plan import CreateInfrastructurePlanUseCase
from application.commands.create_migration_plan import CreateMigrationPlanUseCase
from application.commands.create_monitoring_dashboard import CreateMonitoringDashboardUseCase

# Use cases
from application.commands.create_programme import CreateProgrammeUseCase
from application.commands.estimate_costs import EstimateCostsUseCase
from application.commands.evaluate_gate import EvaluateGateUseCase
from application.commands.execute_migration_step import ExecuteMigrationStepUseCase
from application.commands.export_remediation_backlog import ExportRemediationBacklogUseCase
from application.commands.export_test_scenarios import ExportTestScenariosUseCase
from application.commands.generate_board_presentation import GenerateBoardPresentationUseCase
from application.commands.generate_interface_tests import GenerateInterfaceTestsUseCase
from application.commands.generate_lessons_learned import GenerateLessonsLearnedUseCase
from application.commands.generate_runbook import GenerateRunbookUseCase
from application.commands.generate_terraform import GenerateTerraformUseCase
from application.commands.generate_test_scenarios import GenerateTestScenariosUseCase
from application.commands.generate_transformation_rules import GenerateTransformationRulesUseCase
from application.commands.log_hypercare_incident import LogHypercareIncidentUseCase
from application.commands.run_abap_analysis import RunABAPAnalysisUseCase
from application.commands.run_agent_task import RunAgentTaskUseCase
from application.commands.run_data_profiling import RunDataProfilingUseCase
from application.commands.run_migration_batch import RunMigrationBatchUseCase
from application.commands.run_readiness_check import RunReadinessCheckUseCase
from application.commands.start_cutover import StartCutoverUseCase
from application.commands.start_discovery import StartDiscoveryUseCase
from application.commands.start_hypercare import StartHypercareUseCase
from application.commands.update_cutover_task import UpdateCutoverTaskUseCase
from application.commands.upload_abap_source import UploadABAPSourceUseCase
from application.commands.upload_data_export import UploadDataExportUseCase
from application.queries.get_analysis_results import GetAnalysisResultsQuery
from application.queries.get_audit_log import GetAuditLogQuery
from application.queries.get_benchmark_estimate import GetBenchmarkEstimateQuery
from application.queries.get_cutover_status import GetCutoverStatusQuery
from application.queries.get_data_profiling_results import GetDataProfilingResultsQuery
from application.queries.get_hypercare_status import GetHypercareStatusQuery
from application.queries.get_infrastructure_plan import GetInfrastructurePlanQuery
from application.queries.get_migration_status import GetMigrationStatusQuery

# Queries
from application.queries.get_programme import GetProgrammeQuery
from application.queries.get_test_results import GetTestResultsQuery
from application.queries.get_traceability_matrix import GetTraceabilityMatrixQuery
from application.queries.list_programmes import ListProgrammesQuery
from domain.services.agent_tool_registry import AgentToolRegistry
from domain.services.anomaly_detection_service import AnomalyDetectionService
from domain.services.benchmark_estimation_service import BenchmarkEstimationService
from domain.services.bp_consolidation_service import BPConsolidationService
from domain.services.data_quality_service import DataQualityService
from domain.services.gate_evaluation_service import GateEvaluationService
from domain.services.lessons_learned_service import LessonsLearnedService
from domain.services.plan_validation_service import PlanValidationService
from domain.services.runbook_generation_service import RunbookGenerationService
from domain.services.sizing_service import SAPSizingService
from domain.services.task_graph_service import TaskGraphService

# --- Multi-tenancy ---
from domain.services.tenant_access_service import TenantAccessService
from domain.services.universal_journal_service import UniversalJournalService
from infrastructure.adapters.ai_anomaly_detection_adapter import AIAnomalyDetectionAdapter
from infrastructure.adapters.ai_runbook_generator import AIRunbookGeneratorAdapter
from infrastructure.adapters.ai_transformation_adapter import AITransformationAdapter
from infrastructure.adapters.claude_agent_executor import ClaudeAgentExecutor

# Adapters
from infrastructure.adapters.claude_analysis_adapter import ClaudeAnalysisAdapter
from infrastructure.adapters.claude_migration_advisor import ClaudeMigrationAdvisor
from infrastructure.adapters.claude_test_generator import ClaudeTestGeneratorAdapter
from infrastructure.adapters.cloud_build_provisioning_adapter import CloudBuildProvisioningAdapter
from infrastructure.adapters.cloud_monitoring_adapter import CloudMonitoringAdapter
from infrastructure.adapters.data_profiling_adapter import LocalDataProfilingAdapter
from infrastructure.adapters.gcs_storage_adapter import LocalFileStorageAdapter
from infrastructure.adapters.migration_executor_adapter import StubMigrationExecutor
from infrastructure.adapters.notification_adapter import LoggingNotificationAdapter
from infrastructure.adapters.pubsub_event_bus_adapter import InMemoryEventBusAdapter
from infrastructure.adapters.quick_sizer_parser import QuickSizerXMLParser

# Remediation export
from infrastructure.adapters.remediation_exporter_adapter import RemediationExporterAdapter
from infrastructure.adapters.report_generator_adapter import SimpleReportGenerator

# --- RISE with SAP ---
from infrastructure.adapters.rise_connector_adapter import RISEConnectorAdapter
from infrastructure.adapters.sap_rfc_adapter import SAPRFCAdapter
from infrastructure.adapters.system_health_adapter import StubSystemHealthAdapter
from infrastructure.adapters.test_exporter_adapter import TestExporterAdapter
from infrastructure.adapters.ticketing_adapter import StubTicketingAdapter
from infrastructure.auth.jwt_handler import JWTHandler
from infrastructure.config.settings import Settings, get_settings
from infrastructure.repositories.firestore_anomaly_repo import FirestoreAnomalyRepository
from infrastructure.repositories.firestore_audit_repo import FirestoreAuditRepository
from infrastructure.repositories.firestore_custom_object_repo import FirestoreCustomObjectRepository
from infrastructure.repositories.firestore_cutover_execution_repo import FirestoreCutoverExecutionRepository
from infrastructure.repositories.firestore_data_domain_repo import FirestoreDataDomainRepository
from infrastructure.repositories.firestore_hypercare_repo import FirestoreHypercareRepository
from infrastructure.repositories.firestore_infra_plan_repo import FirestoreInfrastructurePlanRepository
from infrastructure.repositories.firestore_landscape_repo import FirestoreLandscapeRepository
from infrastructure.repositories.firestore_migration_task_repo import FirestoreMigrationTaskRepository

# Firestore repositories (production)
from infrastructure.repositories.firestore_programme_repo import FirestoreProgrammeRepository

# Repositories (in-memory for dev)
from infrastructure.repositories.firestore_programme_repository import (
    InMemoryProgrammeRepository,
)
from infrastructure.repositories.firestore_remediation_repo import FirestoreRemediationRepository
from infrastructure.repositories.firestore_runbook_repo import FirestoreRunbookRepository
from infrastructure.repositories.firestore_test_repo import (
    FirestoreTestScenarioRepository,
    FirestoreTestSuiteRepository,
)

# --- Agentic Execution ---
from infrastructure.repositories.in_memory_agent_task_repository import InMemoryAgentTaskRepository
from infrastructure.repositories.in_memory_anomaly_repository import InMemoryAnomalyRepository
from infrastructure.repositories.in_memory_audit_repository import InMemoryAuditRepository

# --- Migration Benchmarks ---
from infrastructure.repositories.in_memory_benchmark_repository import InMemoryBenchmarkRepository
from infrastructure.repositories.in_memory_custom_object_repository import (
    InMemoryCustomObjectRepository,
)
from infrastructure.repositories.in_memory_cutover_execution_repository import InMemoryCutoverExecutionRepository

# --- Module 03: Data Readiness ---
from infrastructure.repositories.in_memory_data_repository import InMemoryDataRepository
from infrastructure.repositories.in_memory_hypercare_repository import InMemoryHypercareRepository

# --- Module 05: GCP Infrastructure ---
from infrastructure.repositories.in_memory_infrastructure_repository import InMemoryInfrastructurePlanRepository
from infrastructure.repositories.in_memory_landscape_repository import (
    InMemoryLandscapeRepository,
)

# --- Module 06: Migration Orchestrator ---
from infrastructure.repositories.in_memory_migration_task_repository import InMemoryMigrationTaskRepository
from infrastructure.repositories.in_memory_remediation_repository import (
    InMemoryRemediationRepository,
)

# --- Module 07: Cutover Commander ---
from infrastructure.repositories.in_memory_runbook_repository import InMemoryRunbookRepository

# --- Module 04: TestForge ---
from infrastructure.repositories.in_memory_test_scenario_repository import InMemoryTestScenarioRepository
from infrastructure.repositories.in_memory_test_suite_repository import InMemoryTestSuiteRepository
from infrastructure.terraform.terraform_generator import TerraformHCLGenerator


class Container:
    """Dependency injection container — resolves ports to concrete adapters.

    Follows the composition root pattern: all wiring decisions live here
    and nowhere else.  Singletons are cached after first creation.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._singletons: dict[str, Any] = {}

    @property
    def settings(self) -> Settings:
        return self._settings

    # ------------------------------------------------------------------
    # Singleton helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, key: str, factory: Any) -> Any:
        if key not in self._singletons:
            self._singletons[key] = factory()
        return self._singletons[key]

    def _firestore_kwargs(self) -> dict:
        """Common kwargs for Firestore repository constructors."""
        return {
            "project_id": self._settings.gcp_project_id or None,
            "database": self._settings.firestore_database,
        }

    # ------------------------------------------------------------------
    # Core / Auth
    # ------------------------------------------------------------------

    def jwt_handler(self) -> JWTHandler:
        return self._get_or_create(
            "JWTHandler",
            lambda: JWTHandler(
                secret=self._settings.jwt_secret,
                algorithm=self._settings.jwt_algorithm,
                expiry_seconds=self._settings.jwt_expiry_minutes * 60,
            ),
        )

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    def programme_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "ProgrammeRepositoryPort",
                lambda: FirestoreProgrammeRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("ProgrammeRepositoryPort", InMemoryProgrammeRepository)

    def landscape_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "LandscapeRepositoryPort",
                lambda: FirestoreLandscapeRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("LandscapeRepositoryPort", InMemoryLandscapeRepository)

    def custom_object_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "CustomObjectRepositoryPort",
                lambda: FirestoreCustomObjectRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("CustomObjectRepositoryPort", InMemoryCustomObjectRepository)

    def remediation_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "RemediationRepositoryPort",
                lambda: FirestoreRemediationRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("RemediationRepositoryPort", InMemoryRemediationRepository)

    # ------------------------------------------------------------------
    # Adapters
    # ------------------------------------------------------------------

    def abap_analysis(self) -> ClaudeAnalysisAdapter:
        return self._get_or_create(
            "ABAPAnalysisPort",
            lambda: ClaudeAnalysisAdapter(
                api_key=self._settings.anthropic_api_key,
            ),
        )

    def migration_advisor(self) -> ClaudeMigrationAdvisor:
        return self._get_or_create(
            "MigrationAdvisorPort",
            lambda: ClaudeMigrationAdvisor(
                api_key=self._settings.anthropic_api_key,
            ),
        )

    def sap_discovery(self) -> SAPRFCAdapter:
        return self._get_or_create(
            "SAPDiscoveryPort",
            lambda: SAPRFCAdapter(
                host=self._settings.sap_default_host,
            ),
        )

    def file_storage(self) -> LocalFileStorageAdapter:
        return self._get_or_create(
            "FileStoragePort",
            LocalFileStorageAdapter,
        )

    def event_bus(self) -> InMemoryEventBusAdapter:
        return self._get_or_create(
            "EventBusPort",
            InMemoryEventBusAdapter,
        )

    def report_generator(self) -> SimpleReportGenerator:
        return self._get_or_create(
            "ReportGeneratorPort",
            SimpleReportGenerator,
        )

    def remediation_exporter(self) -> RemediationExporterAdapter:
        return self._get_or_create(
            "RemediationExporterPort",
            RemediationExporterAdapter,
        )

    # ------------------------------------------------------------------
    # Use cases
    # ------------------------------------------------------------------

    def create_programme_use_case(self) -> CreateProgrammeUseCase:
        return self._get_or_create(
            "CreateProgrammeUseCase",
            lambda: CreateProgrammeUseCase(
                repository=self.programme_repository(),
                event_bus=self.event_bus(),
            ),
        )

    def start_discovery_use_case(self) -> StartDiscoveryUseCase:
        return self._get_or_create(
            "StartDiscoveryUseCase",
            lambda: StartDiscoveryUseCase(
                programme_repo=self.programme_repository(),
                landscape_repo=self.landscape_repository(),
                sap_discovery=self.sap_discovery(),
                event_bus=self.event_bus(),
            ),
        )

    def upload_abap_source_use_case(self) -> UploadABAPSourceUseCase:
        return self._get_or_create(
            "UploadABAPSourceUseCase",
            lambda: UploadABAPSourceUseCase(
                storage=self.file_storage(),
                landscape_repo=self.landscape_repository(),
                object_repo=self.custom_object_repository(),
            ),
        )

    def run_abap_analysis_use_case(self) -> RunABAPAnalysisUseCase:
        return self._get_or_create(
            "RunABAPAnalysisUseCase",
            lambda: RunABAPAnalysisUseCase(
                object_repo=self.custom_object_repository(),
                remediation_repo=self.remediation_repository(),
                ai_analysis=self.abap_analysis(),
                event_bus=self.event_bus(),
            ),
        )

    def generate_board_presentation_use_case(self) -> GenerateBoardPresentationUseCase:
        return self._get_or_create(
            "GenerateBoardPresentationUseCase",
            lambda: GenerateBoardPresentationUseCase(
                programme_repo=self.programme_repository(),
                landscape_repo=self.landscape_repository(),
                object_repo=self.custom_object_repository(),
                remediation_repo=self.remediation_repository(),
                report_generator=self.report_generator(),
            ),
        )

    def export_remediation_backlog_use_case(self) -> ExportRemediationBacklogUseCase:
        return self._get_or_create(
            "ExportRemediationBacklogUseCase",
            lambda: ExportRemediationBacklogUseCase(
                object_repo=self.custom_object_repository(),
                remediation_repo=self.remediation_repository(),
                exporter=self.remediation_exporter(),
            ),
        )

    # ------------------------------------------------------------------
    # Module 03: Data Readiness repositories & adapters
    # ------------------------------------------------------------------

    def data_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "DataRepositoryPort",
                lambda: FirestoreDataDomainRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("DataRepositoryPort", InMemoryDataRepository)

    def data_profiling(self) -> LocalDataProfilingAdapter:
        return self._get_or_create("DataProfilingPort", LocalDataProfilingAdapter)

    def ai_transformation(self) -> AITransformationAdapter:
        return self._get_or_create(
            "DataTransformationPort",
            lambda: AITransformationAdapter(api_key=self._settings.anthropic_api_key),
        )

    def data_quality_service(self) -> DataQualityService:
        return self._get_or_create("DataQualityService", DataQualityService)

    def bp_consolidation_service(self) -> BPConsolidationService:
        return self._get_or_create("BPConsolidationService", BPConsolidationService)

    def universal_journal_service(self) -> UniversalJournalService:
        return self._get_or_create("UniversalJournalService", UniversalJournalService)

    # Module 03: Use cases

    def upload_data_export_use_case(self) -> UploadDataExportUseCase:
        return self._get_or_create(
            "UploadDataExportUseCase",
            lambda: UploadDataExportUseCase(
                storage=self.file_storage(),
                landscape_repo=self.landscape_repository(),
                data_repo=self.data_repository(),
                event_bus=self.event_bus(),
            ),
        )

    def run_data_profiling_use_case(self) -> RunDataProfilingUseCase:
        return self._get_or_create(
            "RunDataProfilingUseCase",
            lambda: RunDataProfilingUseCase(
                data_repo=self.data_repository(),
                profiling_port=self.data_profiling(),
                quality_service=self.data_quality_service(),
                event_bus=self.event_bus(),
            ),
        )

    def assess_bp_consolidation_use_case(self) -> AssessBPConsolidationUseCase:
        return self._get_or_create(
            "AssessBPConsolidationUseCase",
            lambda: AssessBPConsolidationUseCase(
                bp_service=self.bp_consolidation_service(),
            ),
        )

    def assess_universal_journal_use_case(self) -> AssessUniversalJournalUseCase:
        return self._get_or_create(
            "AssessUniversalJournalUseCase",
            lambda: AssessUniversalJournalUseCase(
                uj_service=self.universal_journal_service(),
            ),
        )

    def generate_transformation_rules_use_case(self) -> GenerateTransformationRulesUseCase:
        return self._get_or_create(
            "GenerateTransformationRulesUseCase",
            lambda: GenerateTransformationRulesUseCase(
                data_repo=self.data_repository(),
                transformation_port=self.ai_transformation(),
                event_bus=self.event_bus(),
            ),
        )

    def get_data_profiling_results_query(self) -> GetDataProfilingResultsQuery:
        return self._get_or_create(
            "GetDataProfilingResultsQuery",
            lambda: GetDataProfilingResultsQuery(
                data_repo=self.data_repository(),
                quality_service=self.data_quality_service(),
            ),
        )

    # ------------------------------------------------------------------
    # Module 04: TestForge repositories & adapters
    # ------------------------------------------------------------------

    def test_scenario_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "TestScenarioRepositoryPort",
                lambda: FirestoreTestScenarioRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("TestScenarioRepositoryPort", InMemoryTestScenarioRepository)

    def test_suite_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "TestSuiteRepositoryPort",
                lambda: FirestoreTestSuiteRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("TestSuiteRepositoryPort", InMemoryTestSuiteRepository)

    def test_generator(self) -> ClaudeTestGeneratorAdapter:
        return self._get_or_create(
            "TestGeneratorPort",
            lambda: ClaudeTestGeneratorAdapter(api_key=self._settings.anthropic_api_key),
        )

    def test_exporter(self) -> TestExporterAdapter:
        return self._get_or_create("TestExporterPort", TestExporterAdapter)

    # Module 04: Use cases

    def generate_test_scenarios_use_case(self) -> GenerateTestScenariosUseCase:
        return self._get_or_create(
            "GenerateTestScenariosUseCase",
            lambda: GenerateTestScenariosUseCase(
                scenario_repo=self.test_scenario_repository(),
                suite_repo=self.test_suite_repository(),
                test_generator=self.test_generator(),
                event_bus=self.event_bus(),
            ),
        )

    def generate_interface_tests_use_case(self) -> GenerateInterfaceTestsUseCase:
        return self._get_or_create(
            "GenerateInterfaceTestsUseCase",
            lambda: GenerateInterfaceTestsUseCase(
                scenario_repo=self.test_scenario_repository(),
                test_generator=self.test_generator(),
                event_bus=self.event_bus(),
            ),
        )

    def export_test_scenarios_use_case(self) -> ExportTestScenariosUseCase:
        return self._get_or_create(
            "ExportTestScenariosUseCase",
            lambda: ExportTestScenariosUseCase(
                scenario_repo=self.test_scenario_repository(),
                exporter=self.test_exporter(),
                event_bus=self.event_bus(),
            ),
        )

    def get_test_results_query(self) -> GetTestResultsQuery:
        return self._get_or_create(
            "GetTestResultsQuery",
            lambda: GetTestResultsQuery(
                scenario_repo=self.test_scenario_repository(),
            ),
        )

    def get_traceability_matrix_query(self) -> GetTraceabilityMatrixQuery:
        return self._get_or_create(
            "GetTraceabilityMatrixQuery",
            lambda: GetTraceabilityMatrixQuery(
                scenario_repo=self.test_scenario_repository(),
            ),
        )

    # ------------------------------------------------------------------
    # Module 05: GCP Infrastructure repositories & adapters
    # ------------------------------------------------------------------

    def infrastructure_plan_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "InfrastructurePlanRepositoryPort",
                lambda: FirestoreInfrastructurePlanRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("InfrastructurePlanRepositoryPort", InMemoryInfrastructurePlanRepository)

    def quick_sizer_parser(self) -> QuickSizerXMLParser:
        return self._get_or_create("QuickSizerParserPort", QuickSizerXMLParser)

    def terraform_generator(self) -> TerraformHCLGenerator:
        return self._get_or_create("TerraformGeneratorPort", TerraformHCLGenerator)

    def sizing_service(self) -> SAPSizingService:
        return self._get_or_create("SAPSizingService", SAPSizingService)

    def plan_validation_service(self) -> PlanValidationService:
        return self._get_or_create("PlanValidationService", PlanValidationService)

    def provisioning_adapter(self) -> CloudBuildProvisioningAdapter:
        return self._get_or_create(
            "ProvisioningPort",
            lambda: CloudBuildProvisioningAdapter(
                gcp_project_id=self._settings.gcp_project_id,
            ),
        )

    # Module 05: Use cases

    def create_infrastructure_plan_use_case(self) -> CreateInfrastructurePlanUseCase:
        return self._get_or_create(
            "CreateInfrastructurePlanUseCase",
            lambda: CreateInfrastructurePlanUseCase(
                programme_repo=self.programme_repository(),
                plan_repo=self.infrastructure_plan_repository(),
                sizing_service=self.sizing_service(),
                validation_service=self.plan_validation_service(),
                quick_sizer_parser=self.quick_sizer_parser(),
                event_bus=self.event_bus(),
            ),
        )

    def generate_terraform_use_case(self) -> GenerateTerraformUseCase:
        return self._get_or_create(
            "GenerateTerraformUseCase",
            lambda: GenerateTerraformUseCase(
                plan_repo=self.infrastructure_plan_repository(),
                terraform_generator=self.terraform_generator(),
                validation_service=self.plan_validation_service(),
                event_bus=self.event_bus(),
            ),
        )

    def estimate_costs_use_case(self) -> EstimateCostsUseCase:
        return self._get_or_create(
            "EstimateCostsUseCase",
            lambda: EstimateCostsUseCase(
                plan_repo=self.infrastructure_plan_repository(),
                sizing_service=self.sizing_service(),
            ),
        )

    def get_infrastructure_plan_query(self) -> GetInfrastructurePlanQuery:
        return self._get_or_create(
            "GetInfrastructurePlanQuery",
            lambda: GetInfrastructurePlanQuery(
                plan_repo=self.infrastructure_plan_repository(),
            ),
        )

    def cloud_monitoring(self) -> CloudMonitoringAdapter:
        return self._get_or_create(
            "CloudMonitoringPort",
            lambda: CloudMonitoringAdapter(
                gcp_project_id=self._settings.gcp_project_id,
            ),
        )

    def create_monitoring_dashboard_use_case(self) -> CreateMonitoringDashboardUseCase:
        return self._get_or_create(
            "CreateMonitoringDashboardUseCase",
            lambda: CreateMonitoringDashboardUseCase(
                plan_repo=self.infrastructure_plan_repository(),
                monitoring=self.cloud_monitoring(),
            ),
        )

    # ------------------------------------------------------------------
    # Module 06: Migration Orchestrator repositories, adapters & services
    # ------------------------------------------------------------------

    def migration_task_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "MigrationTaskRepositoryPort",
                lambda: FirestoreMigrationTaskRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("MigrationTaskRepositoryPort", InMemoryMigrationTaskRepository)

    def audit_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "AuditRepositoryPort",
                lambda: FirestoreAuditRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("AuditRepositoryPort", InMemoryAuditRepository)

    def anomaly_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "AnomalyRepositoryPort",
                lambda: FirestoreAnomalyRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("AnomalyRepositoryPort", InMemoryAnomalyRepository)

    def migration_executor(self) -> StubMigrationExecutor:
        return self._get_or_create(
            "MigrationExecutorPort",
            lambda: StubMigrationExecutor(force_success=True),
        )

    def ai_anomaly_detection(self) -> AIAnomalyDetectionAdapter:
        return self._get_or_create("AnomalyDetectionPort", AIAnomalyDetectionAdapter)

    def task_graph_service(self) -> TaskGraphService:
        return self._get_or_create("TaskGraphService", TaskGraphService)

    def anomaly_detection_service(self) -> AnomalyDetectionService:
        return self._get_or_create("AnomalyDetectionService", AnomalyDetectionService)

    # Module 06: Use cases

    def create_migration_plan_use_case(self) -> CreateMigrationPlanUseCase:
        return self._get_or_create(
            "CreateMigrationPlanUseCase",
            lambda: CreateMigrationPlanUseCase(
                programme_repo=self.programme_repository(),
                task_repo=self.migration_task_repository(),
                audit_repo=self.audit_repository(),
                task_graph_service=self.task_graph_service(),
                event_bus=self.event_bus(),
            ),
        )

    def execute_migration_step_use_case(self) -> ExecuteMigrationStepUseCase:
        return self._get_or_create(
            "ExecuteMigrationStepUseCase",
            lambda: ExecuteMigrationStepUseCase(
                task_repo=self.migration_task_repository(),
                audit_repo=self.audit_repository(),
                anomaly_repo=self.anomaly_repository(),
                executor=self.migration_executor(),
                anomaly_service=self.anomaly_detection_service(),
                event_bus=self.event_bus(),
            ),
        )

    def run_migration_batch_use_case(self) -> RunMigrationBatchUseCase:
        return self._get_or_create(
            "RunMigrationBatchUseCase",
            lambda: RunMigrationBatchUseCase(
                task_repo=self.migration_task_repository(),
                audit_repo=self.audit_repository(),
                anomaly_repo=self.anomaly_repository(),
                executor=self.migration_executor(),
                anomaly_service=self.anomaly_detection_service(),
                event_bus=self.event_bus(),
            ),
        )

    # Module 06: Queries

    def get_migration_status_query(self) -> GetMigrationStatusQuery:
        return self._get_or_create(
            "GetMigrationStatusQuery",
            lambda: GetMigrationStatusQuery(
                task_repo=self.migration_task_repository(),
                anomaly_repo=self.anomaly_repository(),
                task_graph_service=self.task_graph_service(),
            ),
        )

    def get_audit_log_query(self) -> GetAuditLogQuery:
        return self._get_or_create(
            "GetAuditLogQuery",
            lambda: GetAuditLogQuery(
                audit_repo=self.audit_repository(),
            ),
        )

    # ------------------------------------------------------------------
    # Module 07: Cutover Commander repositories, adapters & services
    # ------------------------------------------------------------------

    def runbook_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "RunbookRepositoryPort",
                lambda: FirestoreRunbookRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("RunbookRepositoryPort", InMemoryRunbookRepository)

    def cutover_execution_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "CutoverExecutionRepositoryPort",
                lambda: FirestoreCutoverExecutionRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("CutoverExecutionRepositoryPort", InMemoryCutoverExecutionRepository)

    def hypercare_repository(self) -> Any:
        if self._settings.use_firestore:
            return self._get_or_create(
                "HypercareRepositoryPort",
                lambda: FirestoreHypercareRepository(**self._firestore_kwargs()),
            )
        return self._get_or_create("HypercareRepositoryPort", InMemoryHypercareRepository)

    def ai_runbook_generator(self) -> AIRunbookGeneratorAdapter:
        return self._get_or_create(
            "RunbookAIGeneratorPort",
            lambda: AIRunbookGeneratorAdapter(api_key=self._settings.anthropic_api_key),
        )

    def system_health_adapter(self) -> StubSystemHealthAdapter:
        return self._get_or_create("SystemHealthCheckPort", StubSystemHealthAdapter)

    def notification_adapter(self) -> LoggingNotificationAdapter:
        return self._get_or_create("NotificationPort", LoggingNotificationAdapter)

    def ticketing_adapter(self) -> StubTicketingAdapter:
        return self._get_or_create("TicketingPort", StubTicketingAdapter)

    def runbook_generation_service(self) -> RunbookGenerationService:
        return self._get_or_create("RunbookGenerationService", RunbookGenerationService)

    def gate_evaluation_service(self) -> GateEvaluationService:
        return self._get_or_create("GateEvaluationService", GateEvaluationService)

    def lessons_learned_service(self) -> LessonsLearnedService:
        return self._get_or_create("LessonsLearnedService", LessonsLearnedService)

    # Module 07: Use cases

    def generate_runbook_use_case(self) -> GenerateRunbookUseCase:
        return self._get_or_create(
            "GenerateRunbookUseCase",
            lambda: GenerateRunbookUseCase(
                runbook_repository=self.runbook_repository(),
                event_bus=self.event_bus(),
                generation_service=self.runbook_generation_service(),
            ),
        )

    def approve_runbook_use_case(self) -> ApproveRunbookUseCase:
        return self._get_or_create(
            "ApproveRunbookUseCase",
            lambda: ApproveRunbookUseCase(
                runbook_repository=self.runbook_repository(),
                event_bus=self.event_bus(),
            ),
        )

    def start_cutover_use_case(self) -> StartCutoverUseCase:
        return self._get_or_create(
            "StartCutoverUseCase",
            lambda: StartCutoverUseCase(
                runbook_repository=self.runbook_repository(),
                execution_repository=self.cutover_execution_repository(),
                event_bus=self.event_bus(),
            ),
        )

    def evaluate_gate_use_case(self) -> EvaluateGateUseCase:
        return self._get_or_create(
            "EvaluateGateUseCase",
            lambda: EvaluateGateUseCase(
                runbook_repository=self.runbook_repository(),
                execution_repository=self.cutover_execution_repository(),
                event_bus=self.event_bus(),
                gate_service=self.gate_evaluation_service(),
            ),
        )

    def update_cutover_task_use_case(self) -> UpdateCutoverTaskUseCase:
        return self._get_or_create(
            "UpdateCutoverTaskUseCase",
            lambda: UpdateCutoverTaskUseCase(
                execution_repository=self.cutover_execution_repository(),
                event_bus=self.event_bus(),
            ),
        )

    def start_hypercare_use_case(self) -> StartHypercareUseCase:
        return self._get_or_create(
            "StartHypercareUseCase",
            lambda: StartHypercareUseCase(
                hypercare_repository=self.hypercare_repository(),
                event_bus=self.event_bus(),
            ),
        )

    def log_hypercare_incident_use_case(self) -> LogHypercareIncidentUseCase:
        return self._get_or_create(
            "LogHypercareIncidentUseCase",
            lambda: LogHypercareIncidentUseCase(
                hypercare_repository=self.hypercare_repository(),
                event_bus=self.event_bus(),
                ticketing=self.ticketing_adapter(),
            ),
        )

    def generate_lessons_learned_use_case(self) -> GenerateLessonsLearnedUseCase:
        return self._get_or_create(
            "GenerateLessonsLearnedUseCase",
            lambda: GenerateLessonsLearnedUseCase(
                execution_repository=self.cutover_execution_repository(),
                hypercare_repository=self.hypercare_repository(),
                event_bus=self.event_bus(),
                lessons_service=self.lessons_learned_service(),
            ),
        )

    # Module 07: Queries

    def get_cutover_status_query(self) -> GetCutoverStatusQuery:
        return self._get_or_create(
            "GetCutoverStatusQuery",
            lambda: GetCutoverStatusQuery(
                runbook_repository=self.runbook_repository(),
                execution_repository=self.cutover_execution_repository(),
            ),
        )

    def get_hypercare_status_query(self) -> GetHypercareStatusQuery:
        return self._get_or_create(
            "GetHypercareStatusQuery",
            lambda: GetHypercareStatusQuery(
                hypercare_repository=self.hypercare_repository(),
            ),
        )

    # ------------------------------------------------------------------
    # Queries (Phase 1)
    # ------------------------------------------------------------------

    def get_programme_query(self) -> GetProgrammeQuery:
        return self._get_or_create(
            "GetProgrammeQuery",
            lambda: GetProgrammeQuery(
                repository=self.programme_repository(),
            ),
        )

    def list_programmes_query(self) -> ListProgrammesQuery:
        return self._get_or_create(
            "ListProgrammesQuery",
            lambda: ListProgrammesQuery(
                repository=self.programme_repository(),
            ),
        )

    def get_analysis_results_query(self) -> GetAnalysisResultsQuery:
        return self._get_or_create(
            "GetAnalysisResultsQuery",
            lambda: GetAnalysisResultsQuery(
                object_repo=self.custom_object_repository(),
                remediation_repo=self.remediation_repository(),
            ),
        )

    # ------------------------------------------------------------------
    # Agentic Execution
    # ------------------------------------------------------------------

    def agent_task_repository(self) -> Any:
        return self._get_or_create("AgentTaskRepositoryPort", InMemoryAgentTaskRepository)

    def agent_executor(self) -> Any:
        return self._get_or_create(
            "AgentExecutorPort",
            lambda: ClaudeAgentExecutor(api_key=self._settings.anthropic_api_key),
        )

    def agent_tool_registry(self) -> AgentToolRegistry:
        return self._get_or_create("AgentToolRegistry", AgentToolRegistry)

    def run_agent_task_use_case(self) -> RunAgentTaskUseCase:
        return self._get_or_create(
            "RunAgentTaskUseCase",
            lambda: RunAgentTaskUseCase(
                agent_task_repo=self.agent_task_repository(),
                agent_executor=self.agent_executor(),
                tool_registry=self.agent_tool_registry(),
            ),
        )

    # ------------------------------------------------------------------
    # RISE with SAP
    # ------------------------------------------------------------------

    def rise_connector(self) -> Any:
        return self._get_or_create("RISEConnectorPort", RISEConnectorAdapter)

    def run_readiness_check_use_case(self) -> RunReadinessCheckUseCase:
        return self._get_or_create(
            "RunReadinessCheckUseCase",
            lambda: RunReadinessCheckUseCase(
                programme_repo=self.programme_repository(),
                rise_connector=self.rise_connector(),
            ),
        )

    # ------------------------------------------------------------------
    # Migration Benchmarks
    # ------------------------------------------------------------------

    def benchmark_repository(self) -> Any:
        return self._get_or_create("BenchmarkRepositoryPort", InMemoryBenchmarkRepository)

    def benchmark_estimation_service(self) -> BenchmarkEstimationService:
        return self._get_or_create("BenchmarkEstimationService", BenchmarkEstimationService)

    def get_benchmark_estimate_query(self) -> GetBenchmarkEstimateQuery:
        return self._get_or_create(
            "GetBenchmarkEstimateQuery",
            lambda: GetBenchmarkEstimateQuery(
                programme_repo=self.programme_repository(),
                landscape_repo=self.landscape_repository(),
                benchmark_repo=self.benchmark_repository(),
                estimation_service=self.benchmark_estimation_service(),
            ),
        )

    # ------------------------------------------------------------------
    # Multi-tenancy
    # ------------------------------------------------------------------

    def tenant_access_service(self) -> TenantAccessService:
        return self._get_or_create(
            "TenantAccessService",
            lambda: TenantAccessService(
                programme_repository=self.programme_repository(),
            ),
        )

    # ------------------------------------------------------------------
    # Generic resolver
    # ------------------------------------------------------------------

    def resolve(self, key: Any) -> Any:
        """Resolve a dependency by class type or string name.

        Accepts both class types (e.g. CreateProgrammeUseCase) and string
        names (e.g. 'CreateProgrammeUseCase').
        """
        type_name = key if isinstance(key, str) else key.__name__

        resolver_map: dict[str, Any] = {
            # --- Core / Auth ---
            "Settings": lambda: self._settings,
            "JWTHandler": self.jwt_handler,
            # --- Phase 1: Ports / repositories ---
            "ProgrammeRepositoryPort": self.programme_repository,
            "LandscapeRepositoryPort": self.landscape_repository,
            "CustomObjectRepositoryPort": self.custom_object_repository,
            "RemediationRepositoryPort": self.remediation_repository,
            "ABAPAnalysisPort": self.abap_analysis,
            "MigrationAdvisorPort": self.migration_advisor,
            "SAPDiscoveryPort": self.sap_discovery,
            "FileStoragePort": self.file_storage,
            "EventBusPort": self.event_bus,
            "ReportGeneratorPort": self.report_generator,
            "RemediationExporterPort": self.remediation_exporter,
            # Phase 1: Use cases
            "CreateProgrammeUseCase": self.create_programme_use_case,
            "StartDiscoveryUseCase": self.start_discovery_use_case,
            "UploadABAPSourceUseCase": self.upload_abap_source_use_case,
            "RunABAPAnalysisUseCase": self.run_abap_analysis_use_case,
            "GenerateBoardPresentationUseCase": self.generate_board_presentation_use_case,
            "ExportRemediationBacklogUseCase": self.export_remediation_backlog_use_case,
            # Phase 1: Queries
            "GetProgrammeQuery": self.get_programme_query,
            "ListProgrammesQuery": self.list_programmes_query,
            "GetAnalysisResultsQuery": self.get_analysis_results_query,
            # --- Module 03: Data Readiness ---
            "DataRepositoryPort": self.data_repository,
            "DataProfilingPort": self.data_profiling,
            "DataTransformationPort": self.ai_transformation,
            "UploadDataExportUseCase": self.upload_data_export_use_case,
            "RunDataProfilingUseCase": self.run_data_profiling_use_case,
            "AssessBPConsolidationUseCase": self.assess_bp_consolidation_use_case,
            "AssessUniversalJournalUseCase": self.assess_universal_journal_use_case,
            "GenerateTransformationRulesUseCase": self.generate_transformation_rules_use_case,
            "GetDataProfilingResultsQuery": self.get_data_profiling_results_query,
            # --- Module 04: TestForge ---
            "TestScenarioRepositoryPort": self.test_scenario_repository,
            "TestSuiteRepositoryPort": self.test_suite_repository,
            "TestGeneratorPort": self.test_generator,
            "TestExporterPort": self.test_exporter,
            "GenerateTestScenariosUseCase": self.generate_test_scenarios_use_case,
            "GenerateInterfaceTestsUseCase": self.generate_interface_tests_use_case,
            "ExportTestScenariosUseCase": self.export_test_scenarios_use_case,
            "GetTestResultsQuery": self.get_test_results_query,
            "GetTraceabilityMatrixQuery": self.get_traceability_matrix_query,
            # --- Module 05: GCP Infrastructure ---
            "InfrastructurePlanRepositoryPort": self.infrastructure_plan_repository,
            "QuickSizerParserPort": self.quick_sizer_parser,
            "TerraformGeneratorPort": self.terraform_generator,
            "ProvisioningPort": self.provisioning_adapter,
            "CloudBuildProvisioningAdapter": self.provisioning_adapter,
            "CreateInfrastructurePlanUseCase": self.create_infrastructure_plan_use_case,
            "GenerateTerraformUseCase": self.generate_terraform_use_case,
            "EstimateCostsUseCase": self.estimate_costs_use_case,
            "GetInfrastructurePlanQuery": self.get_infrastructure_plan_query,
            "CloudMonitoringPort": self.cloud_monitoring,
            "CloudMonitoringAdapter": self.cloud_monitoring,
            "CreateMonitoringDashboardUseCase": self.create_monitoring_dashboard_use_case,
            # --- Module 06: Migration Orchestrator ---
            "MigrationTaskRepositoryPort": self.migration_task_repository,
            "InMemoryMigrationTaskRepository": self.migration_task_repository,
            "AuditRepositoryPort": self.audit_repository,
            "InMemoryAuditRepository": self.audit_repository,
            "AnomalyRepositoryPort": self.anomaly_repository,
            "InMemoryAnomalyRepository": self.anomaly_repository,
            "MigrationExecutorPort": self.migration_executor,
            "StubMigrationExecutor": self.migration_executor,
            "AnomalyDetectionPort": self.ai_anomaly_detection,
            "AIAnomalyDetectionAdapter": self.ai_anomaly_detection,
            "TaskGraphService": self.task_graph_service,
            "AnomalyDetectionService": self.anomaly_detection_service,
            "CreateMigrationPlanUseCase": self.create_migration_plan_use_case,
            "ExecuteMigrationStepUseCase": self.execute_migration_step_use_case,
            "RunMigrationBatchUseCase": self.run_migration_batch_use_case,
            "GetMigrationStatusQuery": self.get_migration_status_query,
            "GetAuditLogQuery": self.get_audit_log_query,
            # --- Module 07: Cutover Commander ---
            "RunbookRepositoryPort": self.runbook_repository,
            "InMemoryRunbookRepository": self.runbook_repository,
            "CutoverExecutionRepositoryPort": self.cutover_execution_repository,
            "InMemoryCutoverExecutionRepository": self.cutover_execution_repository,
            "HypercareRepositoryPort": self.hypercare_repository,
            "InMemoryHypercareRepository": self.hypercare_repository,
            "RunbookAIGeneratorPort": self.ai_runbook_generator,
            "AIRunbookGeneratorAdapter": self.ai_runbook_generator,
            "SystemHealthCheckPort": self.system_health_adapter,
            "StubSystemHealthAdapter": self.system_health_adapter,
            "NotificationPort": self.notification_adapter,
            "LoggingNotificationAdapter": self.notification_adapter,
            "TicketingPort": self.ticketing_adapter,
            "StubTicketingAdapter": self.ticketing_adapter,
            "RunbookGenerationService": self.runbook_generation_service,
            "GateEvaluationService": self.gate_evaluation_service,
            "LessonsLearnedService": self.lessons_learned_service,
            "GenerateRunbookUseCase": self.generate_runbook_use_case,
            "ApproveRunbookUseCase": self.approve_runbook_use_case,
            "StartCutoverUseCase": self.start_cutover_use_case,
            "EvaluateGateUseCase": self.evaluate_gate_use_case,
            "UpdateCutoverTaskUseCase": self.update_cutover_task_use_case,
            "StartHypercareUseCase": self.start_hypercare_use_case,
            "LogHypercareIncidentUseCase": self.log_hypercare_incident_use_case,
            "GenerateLessonsLearnedUseCase": self.generate_lessons_learned_use_case,
            "GetCutoverStatusQuery": self.get_cutover_status_query,
            "GetHypercareStatusQuery": self.get_hypercare_status_query,
            # --- Agentic Execution ---
            "AgentTaskRepositoryPort": self.agent_task_repository,
            "AgentExecutorPort": self.agent_executor,
            "AgentToolRegistry": self.agent_tool_registry,
            "RunAgentTaskUseCase": self.run_agent_task_use_case,
            # --- RISE with SAP ---
            "RISEConnectorPort": self.rise_connector,
            "RunReadinessCheckUseCase": self.run_readiness_check_use_case,
            # --- Migration Benchmarks ---
            "BenchmarkRepositoryPort": self.benchmark_repository,
            "BenchmarkEstimationService": self.benchmark_estimation_service,
            "GetBenchmarkEstimateQuery": self.get_benchmark_estimate_query,
            # --- Multi-tenancy ---
            "TenantAccessService": self.tenant_access_service,
        }

        factory = resolver_map.get(type_name)
        if factory is None:
            raise KeyError(
                f"No binding registered for '{type_name}'. Available: {', '.join(sorted(resolver_map.keys()))}"
            )
        return factory()
