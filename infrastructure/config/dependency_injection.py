"""Dependency injection container — composition root for HanaForge.

Wires all infrastructure adapters to domain ports and creates use cases
with their dependencies injected.  This is the single place where concrete
implementations are chosen.
"""

from __future__ import annotations

from typing import Any

from infrastructure.config.settings import Settings, get_settings

# Repositories (in-memory for dev)
from infrastructure.repositories.firestore_programme_repository import (
    InMemoryProgrammeRepository,
)
from infrastructure.repositories.in_memory_landscape_repository import (
    InMemoryLandscapeRepository,
)
from infrastructure.repositories.in_memory_custom_object_repository import (
    InMemoryCustomObjectRepository,
)
from infrastructure.repositories.in_memory_remediation_repository import (
    InMemoryRemediationRepository,
)

# Adapters
from infrastructure.adapters.claude_analysis_adapter import ClaudeAnalysisAdapter
from infrastructure.adapters.claude_migration_advisor import ClaudeMigrationAdvisor
from infrastructure.adapters.sap_rfc_adapter import SAPRFCAdapter
from infrastructure.adapters.gcs_storage_adapter import LocalFileStorageAdapter
from infrastructure.adapters.pubsub_event_bus_adapter import InMemoryEventBusAdapter
from infrastructure.adapters.report_generator_adapter import SimpleReportGenerator

# Use cases
from application.commands.create_programme import CreateProgrammeUseCase
from application.commands.start_discovery import StartDiscoveryUseCase
from application.commands.upload_abap_source import UploadABAPSourceUseCase
from application.commands.run_abap_analysis import RunABAPAnalysisUseCase

# Queries
from application.queries.get_programme import GetProgrammeQuery
from application.queries.list_programmes import ListProgrammesQuery
from application.queries.get_analysis_results import GetAnalysisResultsQuery


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

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    def programme_repository(self) -> InMemoryProgrammeRepository:
        return self._get_or_create(
            "ProgrammeRepositoryPort",
            InMemoryProgrammeRepository,
        )

    def landscape_repository(self) -> InMemoryLandscapeRepository:
        return self._get_or_create(
            "LandscapeRepositoryPort",
            InMemoryLandscapeRepository,
        )

    def custom_object_repository(self) -> InMemoryCustomObjectRepository:
        return self._get_or_create(
            "CustomObjectRepositoryPort",
            InMemoryCustomObjectRepository,
        )

    def remediation_repository(self) -> InMemoryRemediationRepository:
        return self._get_or_create(
            "RemediationRepositoryPort",
            InMemoryRemediationRepository,
        )

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

    # ------------------------------------------------------------------
    # Queries
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
    # Generic resolver
    # ------------------------------------------------------------------

    def resolve(self, key: Any) -> Any:
        """Resolve a dependency by class type or string name.

        Accepts both class types (e.g. CreateProgrammeUseCase) and string
        names (e.g. 'CreateProgrammeUseCase').
        """
        type_name = key if isinstance(key, str) else key.__name__

        _RESOLVER_MAP: dict[str, Any] = {
            # Ports / repositories
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
            # Use cases
            "CreateProgrammeUseCase": self.create_programme_use_case,
            "StartDiscoveryUseCase": self.start_discovery_use_case,
            "UploadABAPSourceUseCase": self.upload_abap_source_use_case,
            "RunABAPAnalysisUseCase": self.run_abap_analysis_use_case,
            # Queries
            "GetProgrammeQuery": self.get_programme_query,
            "ListProgrammesQuery": self.list_programmes_query,
            "GetAnalysisResultsQuery": self.get_analysis_results_query,
        }

        factory = _RESOLVER_MAP.get(type_name)
        if factory is None:
            raise KeyError(
                f"No binding registered for '{type_name}'. "
                f"Available: {', '.join(sorted(_RESOLVER_MAP.keys()))}"
            )
        return factory()
