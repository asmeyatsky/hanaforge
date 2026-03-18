"""ClaudeAnalysisAdapter — implements ABAPAnalysisPort using the Anthropic SDK.

Sends ABAP source code along with SAP Simplification List context to Claude
for compatibility analysis, returning a structured AnalysisResult.
"""

from __future__ import annotations

import json

import anthropic

from domain.ports.ai_analysis_ports import AnalysisResult
from domain.value_objects.object_type import ABAPObjectType


_SYSTEM_PROMPT = """\
You are an SAP S/4HANA migration expert specialising in ABAP code analysis.

Your task is to analyse a custom ABAP object and determine whether it is
compatible with the target SAP S/4HANA version.  Use your knowledge of the
SAP Simplification List, deprecated APIs, obsolete statements, and
S/4HANA data model changes to identify issues.

Key areas to check:
- Deprecated function modules (e.g. BAPI_*, obsolete BAPIs)
- Removed or changed tables (e.g. BSEG direct access, KONV changes)
- Obsolete ABAP statements (MOVE CORRESPONDING with deep structures, etc.)
- Business Partner migration impact (KNA1/LFA1 -> BP)
- Material Ledger / New G/L changes
- Fiori compatibility concerns
- CDS view replacements for classic reports

Return your analysis as a JSON object with EXACTLY this schema:
{
  "compatible": <bool>,
  "compatibility_status": "<one of COMPATIBLE, INCOMPATIBLE, NEEDS_REVIEW>",
  "deprecated_apis": [<list of deprecated API names found>],
  "issues": [<list of human-readable issue descriptions>],
  "issue_type": "<primary issue type: deprecated_api, table_change, statement_obsolete, bp_migration, or null if compatible>",
  "deprecated_api": "<primary deprecated API name or null>",
  "suggested_replacement": "<recommended replacement API/approach or null>",
  "remediation_code": <string with suggested replacement code or null>,
  "generated_code": <string with complete remediated ABAP code or null>,
  "confidence": <float between 0.0 and 1.0>,
  "effort_points": <int 1-5 where 1=trivial, 2=low, 3=medium, 4=high, 5=critical rewrite>
}

Return ONLY the JSON object, no markdown fences or additional text.
"""


class ClaudeAnalysisAdapter:
    """Implements ABAPAnalysisPort by sending ABAP source to Claude for analysis."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def analyze_object(
        self,
        source_code: str,
        object_type: ABAPObjectType,
        sap_source_version: str,
        target_version: str,
    ) -> AnalysisResult:
        user_message = (
            f"Analyse the following ABAP {object_type.value} for compatibility "
            f"when migrating from SAP {sap_source_version} to {target_version}.\n\n"
            f"--- ABAP SOURCE ---\n{source_code}\n--- END SOURCE ---"
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        # Parse the structured JSON response from Claude
        raw_text = response.content[0].text.strip()
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            # If Claude wraps the JSON in markdown fences, strip them
            cleaned = raw_text
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned.strip())

        compatible = parsed.get("compatible", False)
        confidence = float(parsed.get("confidence", 0.5))

        # Derive compatibility_status from compatible flag if not explicitly set
        raw_status = parsed.get("compatibility_status")
        if raw_status:
            compatibility_status = raw_status
        elif compatible:
            compatibility_status = "COMPATIBLE"
        else:
            compatibility_status = "INCOMPATIBLE"

        return AnalysisResult(
            compatible=compatible,
            deprecated_apis=parsed.get("deprecated_apis", []),
            issues=parsed.get("issues", []),
            remediation_code=parsed.get("remediation_code"),
            confidence=confidence,
            compatibility_status=compatibility_status,
            issue_type=parsed.get("issue_type"),
            deprecated_api=parsed.get("deprecated_api"),
            suggested_replacement=parsed.get("suggested_replacement"),
            generated_code=parsed.get("generated_code"),
            confidence_score=confidence,
            effort_points=parsed.get("effort_points"),
        )
