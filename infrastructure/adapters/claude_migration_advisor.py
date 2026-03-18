"""ClaudeMigrationAdvisor — implements MigrationAdvisorPort using the Anthropic SDK.

Takes a landscape summary and asks Claude to recommend a migration approach
(Greenfield, Brownfield, Selective Data Transition, or RISE with SAP).
"""

from __future__ import annotations

import json

import anthropic

from domain.value_objects.migration_approach import (
    MigrationApproach,
    MigrationRecommendation,
)

_SYSTEM_PROMPT = """\
You are a senior SAP S/4HANA migration strategist.

Given a landscape summary containing system metadata (database size, user count,
custom object count, incompatibility ratio, integration points, etc.), recommend
the most appropriate migration approach.

Available approaches:
- GREENFIELD: Full reimplementation — best for heavily customised systems where
  starting fresh provides more value than preserving customisations.
- BROWNFIELD: System conversion in-place — best when custom code is mostly
  compatible and data volume is manageable.
- SELECTIVE_DATA_TRANSITION: Shell conversion with selective data migration —
  good middle ground for moderate complexity.
- RISE_WITH_SAP: Cloud-first managed migration via SAP's RISE programme —
  suitable when the customer wants to move to cloud with SAP managing infra.

Return your recommendation as a JSON object with EXACTLY this schema:
{
  "approach": "<one of GREENFIELD, BROWNFIELD, SELECTIVE_DATA_TRANSITION, RISE_WITH_SAP>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<2-4 sentences explaining why this approach is recommended>"
}

Return ONLY the JSON object, no markdown fences or additional text.
"""


class ClaudeMigrationAdvisor:
    """Implements MigrationAdvisorPort by consulting Claude for strategic advice."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def recommend_approach(self, landscape_summary: dict) -> MigrationRecommendation:
        user_message = (
            "Based on the following SAP landscape summary, recommend the optimal "
            "migration approach to S/4HANA.\n\n"
            f"Landscape Summary:\n{json.dumps(landscape_summary, indent=2)}"
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        first_block = response.content[0]
        if not hasattr(first_block, "text"):
            raise ValueError("Expected a TextBlock response from Claude")
        raw_text = first_block.text.strip()  # type: ignore[union-attr]
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            cleaned = raw_text
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned.strip())

        return MigrationRecommendation(
            approach=MigrationApproach(parsed["approach"]),
            confidence=float(parsed.get("confidence", 0.5)),
            reasoning=parsed.get("reasoning", ""),
        )
