"""Universal Journal service — assesses ACDOCA migration readiness.

Checks for custom FI coding block extensions, profit centre assignments,
and segment reporting configurations that impact S/4HANA migration.
"""

from __future__ import annotations

from domain.value_objects.data_quality import UniversalJournalAssessment

# Standard SAP coding block fields that do NOT count as custom
_STANDARD_CODING_BLOCKS = frozenset(
    {
        "BUKRS",
        "BELNR",
        "GJAHR",
        "BUZEI",
        "KOSTL",
        "PRCTR",
        "SEGMENT",
        "PROFIT_CTR",
        "HKONT",
        "KSTAR",
        "AUFNR",
        "PS_POSID",
        "ANLN1",
        "ANLN2",
        "VBELN",
        "VBEL2",
        "KOKRS",
        "WERKS",
        "GSBER",
        "FKBER",
    }
)


class UniversalJournalService:
    """Assesses Universal Journal migration readiness for S/4HANA."""

    def assess_readiness(
        self,
        fi_config: dict,
        co_config: dict,
    ) -> UniversalJournalAssessment:
        """Evaluate FI and CO configurations for ACDOCA migration impact.

        Args:
            fi_config: FI configuration dict with keys like
                'coding_blocks', 'profit_centres', 'segment_reporting'.
            co_config: CO configuration dict with keys like
                'cost_elements', 'profit_centres', 'internal_orders'.
        """
        # Detect custom coding blocks
        coding_blocks = fi_config.get("coding_blocks", [])
        custom_blocks = tuple(block for block in coding_blocks if block.upper() not in _STANDARD_CODING_BLOCKS)

        # Count profit centre assignments
        fi_profit_centres = fi_config.get("profit_centres", [])
        co_profit_centres = co_config.get("profit_centres", [])
        all_profit_centres = set(fi_profit_centres) | set(co_profit_centres)
        profit_centre_count = len(all_profit_centres)

        # Count segment reporting configurations
        segment_configs = fi_config.get("segment_reporting", [])
        segment_count = len(segment_configs)

        # Assess FI G/L simplification impact
        has_special_ledgers = fi_config.get("special_ledgers", False)
        has_new_gl = fi_config.get("new_gl_active", False)
        has_classic_gl = not has_new_gl

        if has_classic_gl and has_special_ledgers:
            fi_gl_impact = (
                "HIGH — Classic G/L with special ledgers requires full migration "
                "to Universal Journal; all special ledger data must be mapped to ACDOCA"
            )
        elif has_classic_gl:
            fi_gl_impact = "MEDIUM — Classic G/L requires migration to new G/L architecture before ACDOCA conversion"
        elif has_special_ledgers:
            fi_gl_impact = "MEDIUM — New G/L active but special ledgers require mapping to extension ledgers in S/4HANA"
        else:
            fi_gl_impact = "LOW — New G/L already active without special ledgers; straightforward ACDOCA migration"

        # Determine overall migration complexity
        complexity_score = 0
        if len(custom_blocks) > 5:
            complexity_score += 3
        elif len(custom_blocks) > 0:
            complexity_score += 1

        if profit_centre_count > 1000:
            complexity_score += 2
        elif profit_centre_count > 100:
            complexity_score += 1

        if segment_count > 10:
            complexity_score += 2
        elif segment_count > 0:
            complexity_score += 1

        if has_classic_gl:
            complexity_score += 2
        if has_special_ledgers:
            complexity_score += 1

        if complexity_score >= 5:
            migration_complexity = "HIGH"
        elif complexity_score >= 2:
            migration_complexity = "MEDIUM"
        else:
            migration_complexity = "LOW"

        return UniversalJournalAssessment(
            custom_coding_blocks=custom_blocks,
            profit_centre_assignments=profit_centre_count,
            segment_reporting_configs=segment_count,
            fi_gl_simplification_impact=fi_gl_impact,
            migration_complexity=migration_complexity,
        )
