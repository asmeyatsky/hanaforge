"""Tests for SAPSizingService — pure domain logic, no mocks."""

from domain.services.sizing_service import SAPSizingService
from domain.value_objects.gcp_types import (
    GCPMachineType,
    GCPRegion,
    SizingInput,
)
from domain.value_objects.object_type import SystemRole


def _make_sizing(
    *,
    saps: int = 20_000,
    memory_gb: int = 512,
    db_size_gb: float = 500.0,
    users: int = 500,
    landscape: SystemRole = SystemRole.PRD,
) -> SizingInput:
    return SizingInput(
        saps_rating=saps,
        hana_memory_gb=memory_gb,
        db_size_gb=db_size_gb,
        concurrent_users=users,
        landscape_type=landscape,
    )


class TestRecommendHANAConfig:
    """HANA instance selection based on memory requirements."""

    def test_small_hana_sizing_below_256gb(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing(memory_gb=128)

        config = service.recommend_hana_config(sizing)

        assert config.instance_type == GCPMachineType.M3_ULTRAMEM_32
        assert config.memory_gb == 896  # actual memory of the instance

    def test_medium_hana_sizing_512gb(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing(memory_gb=600)

        config = service.recommend_hana_config(sizing)

        assert config.instance_type == GCPMachineType.M3_ULTRAMEM_64
        assert config.memory_gb == 1_792

    def test_large_hana_sizing_above_2tb(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing(memory_gb=3000)

        config = service.recommend_hana_config(sizing)

        assert config.instance_type == GCPMachineType.M2_ULTRAMEM_208
        assert config.memory_gb == 5_888

    def test_very_large_hana_sizing_above_6tb(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing(memory_gb=8000)

        config = service.recommend_hana_config(sizing)

        assert config.instance_type == GCPMachineType.M2_ULTRAMEM_416

    def test_extreme_hana_sizing_above_12tb_baremetal(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing(memory_gb=16000)

        config = service.recommend_hana_config(sizing)

        assert config.instance_type == GCPMachineType.BAREMETAL_BM_HANA

    def test_disk_sizing_proportional_to_db_size(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing(db_size_gb=2000.0)

        config = service.recommend_hana_config(sizing)

        assert config.hana_data_disk_gb == 3000  # 2000 * 1.5
        assert config.hana_log_disk_gb == 1000  # 2000 * 0.5
        assert config.hana_shared_disk_gb == 1024
        assert config.backup_disk_gb == 4000  # 2000 * 2.0

    def test_disk_sizing_enforces_minimums(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing(db_size_gb=100.0)

        config = service.recommend_hana_config(sizing)

        assert config.hana_data_disk_gb >= 256
        assert config.hana_log_disk_gb >= 512
        assert config.backup_disk_gb >= 512


class TestRecommendAppServerConfig:
    """App server selection based on SAPS rating and user count."""

    def test_app_server_sizing_production(self) -> None:
        service = SAPSizingService()

        config = service.recommend_app_server_config(saps=30_000, users=1_000, landscape_type=SystemRole.PRD)

        # 30k SAPS / 1k users maps to C3_STANDARD_44 (30k < 60k threshold)
        assert config.instance_type == GCPMachineType.C3_STANDARD_44
        assert config.instance_count >= 2
        assert config.auto_scaling is True
        assert config.min_instances >= 2
        assert config.max_instances >= config.instance_count

    def test_app_server_sizing_dev(self) -> None:
        service = SAPSizingService()

        config = service.recommend_app_server_config(saps=5_000, users=50, landscape_type=SystemRole.DEV)

        assert config.instance_count == 1
        assert config.auto_scaling is False

    def test_app_server_sizing_qas(self) -> None:
        service = SAPSizingService()

        config = service.recommend_app_server_config(saps=20_000, users=500, landscape_type=SystemRole.QAS)

        assert config.auto_scaling is True
        assert config.min_instances >= 1

    def test_large_app_server_sizing(self) -> None:
        service = SAPSizingService()

        config = service.recommend_app_server_config(saps=100_000, users=10_000, landscape_type=SystemRole.PRD)

        assert config.instance_type == GCPMachineType.C3_HIGHMEM_22
        assert config.instance_count >= 4


class TestCostEstimate:
    """Cost estimation with regional pricing and CUD discounts."""

    def test_cost_estimate_calculation(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing()
        hana = service.recommend_hana_config(sizing)
        app = service.recommend_app_server_config(sizing.saps_rating, sizing.concurrent_users, sizing.landscape_type)

        cost = service.calculate_cost_estimate(
            hana=hana,
            app=app,
            region=GCPRegion.US_CENTRAL1,
            ha_enabled=True,
            dr_enabled=False,
        )

        assert cost.hana_monthly > 0
        assert cost.app_server_monthly > 0
        assert cost.storage_monthly > 0
        assert cost.network_monthly > 0
        assert cost.backup_monthly > 0
        assert cost.monitoring_monthly > 0
        assert cost.total_monthly > cost.hana_monthly  # total > any single component

    def test_cud_discount_applied(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing(memory_gb=3000)
        hana = service.recommend_hana_config(sizing)
        app = service.recommend_app_server_config(sizing.saps_rating, sizing.concurrent_users, sizing.landscape_type)

        cost = service.calculate_cost_estimate(
            hana=hana,
            app=app,
            region=GCPRegion.US_CENTRAL1,
            ha_enabled=True,
            dr_enabled=False,
        )

        # Large HANA instance should get 37% CUD
        assert cost.cud_discount_percentage == 37.0
        assert cost.cud_monthly < cost.total_monthly

    def test_ha_doubles_hana_cost(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing()
        hana = service.recommend_hana_config(sizing)
        app = service.recommend_app_server_config(sizing.saps_rating, sizing.concurrent_users, sizing.landscape_type)

        cost_no_ha = service.calculate_cost_estimate(
            hana=hana,
            app=app,
            region=GCPRegion.US_CENTRAL1,
            ha_enabled=False,
            dr_enabled=False,
        )
        cost_ha = service.calculate_cost_estimate(
            hana=hana,
            app=app,
            region=GCPRegion.US_CENTRAL1,
            ha_enabled=True,
            dr_enabled=False,
        )

        assert cost_ha.hana_monthly > cost_no_ha.hana_monthly

    def test_regional_pricing_multiplier(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing()
        hana = service.recommend_hana_config(sizing)
        app = service.recommend_app_server_config(sizing.saps_rating, sizing.concurrent_users, sizing.landscape_type)

        cost_us = service.calculate_cost_estimate(
            hana=hana,
            app=app,
            region=GCPRegion.US_CENTRAL1,
            ha_enabled=False,
            dr_enabled=False,
        )
        cost_eu = service.calculate_cost_estimate(
            hana=hana,
            app=app,
            region=GCPRegion.EUROPE_WEST3,
            ha_enabled=False,
            dr_enabled=False,
        )

        # Europe should be more expensive
        assert cost_eu.total_monthly > cost_us.total_monthly

    def test_total_annual_is_12x_monthly(self) -> None:
        service = SAPSizingService()
        sizing = _make_sizing()
        hana = service.recommend_hana_config(sizing)
        app = service.recommend_app_server_config(sizing.saps_rating, sizing.concurrent_users, sizing.landscape_type)

        cost = service.calculate_cost_estimate(
            hana=hana,
            app=app,
            region=GCPRegion.US_CENTRAL1,
            ha_enabled=False,
            dr_enabled=False,
        )

        assert abs(cost.total_annual - cost.total_monthly * 12) < 0.01


class TestValidationViaService:
    """Integration of sizing + validation — HA required for PRD."""

    def test_validation_ha_required_for_prd(self) -> None:
        from domain.entities.infrastructure_plan import InfrastructurePlan
        from domain.services.plan_validation_service import PlanValidationService
        from domain.value_objects.gcp_types import (
            NetworkConfig,
            SecurityConfig,
            ValidationStatus,
        )

        service = SAPSizingService()
        sizing = _make_sizing(landscape=SystemRole.PRD)
        hana = service.recommend_hana_config(sizing)
        app = service.recommend_app_server_config(sizing.saps_rating, sizing.concurrent_users, sizing.landscape_type)
        cost = service.calculate_cost_estimate(
            hana=hana,
            app=app,
            region=GCPRegion.US_CENTRAL1,
            ha_enabled=False,
            dr_enabled=False,
        )

        plan = InfrastructurePlan.create(
            id="plan-001",
            programme_id="prog-001",
            region="us-central1",
            dr_region=None,
            hana_config=hana,
            app_server_config=app,
            network_config=NetworkConfig(
                vpc_name="sap-vpc",
                subnet_cidr_db="10.0.1.0/24",
                subnet_cidr_app="10.0.2.0/24",
                subnet_cidr_web="10.0.3.0/24",
                enable_cloud_nat=True,
                enable_private_google_access=True,
                interconnect_bandwidth_gbps=None,
            ),
            ha_enabled=False,  # HA disabled for PRD
            dr_enabled=False,
            security_config=SecurityConfig(
                enable_cmek=False,
                enable_vpc_sc=False,
                enable_os_login=True,
                enable_binary_auth=False,
                kms_key_ring=None,
            ),
            estimated_monthly_cost=cost,
        )

        validator = PlanValidationService()
        result = validator.validate_sap_certification(plan)

        # Should have warnings about HA, DR, and CMEK
        assert result.status == ValidationStatus.WARNINGS
        assert any("High availability" in w for w in result.warnings)
        assert any("Disaster recovery" in w for w in result.warnings)
        assert any("CMEK" in w for w in result.warnings)
