"""AITransformationAdapter — uses Claude to generate LTMC-compatible transformation rules."""

from __future__ import annotations

import json

import anthropic

from domain.value_objects.data_quality import TransformationRule, TransformationRuleType


_SYSTEM_PROMPT = """\
You are an SAP S/4HANA data migration expert specialising in LTMC
(Legacy Transfer Migration Cockpit) data transformation rules.

Given a source schema, target schema, and optional sample data, generate
transformation rules that map source fields to S/4HANA target fields.

Consider:
- Business Partner (BP) model changes (KNA1/LFA1 -> BP)
- Universal Journal (ACDOCA) field mappings
- Material master simplifications
- S/4HANA field length changes and data type conversions
- Value mappings for changed domain values

Return your rules as a JSON array with EXACTLY this schema per rule:
[
  {
    "source_field": "<source field name>",
    "target_field": "<target field name>",
    "rule_type": "<DIRECT_MAP|VALUE_MAP|CONCATENATE|SPLIT|LOOKUP|CUSTOM>",
    "rule_expression": "<transformation expression or mapping>",
    "description": "<human-readable description of the rule>"
  }
]

Return ONLY the JSON array, no markdown fences or additional text.
"""


class AITransformationAdapter:
    """Implements DataTransformationPort using Claude for AI-powered rule generation."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate_rules(
        self,
        source_schema: dict,
        target_schema: dict,
        sample_data: list[dict],
    ) -> list[TransformationRule]:
        user_message = (
            f"Generate LTMC-compatible transformation rules for the following migration:\n\n"
            f"SOURCE SCHEMA:\n{json.dumps(source_schema, indent=2)}\n\n"
            f"TARGET SCHEMA:\n{json.dumps(target_schema, indent=2)}\n\n"
        )
        if sample_data:
            user_message += f"SAMPLE DATA (first 5 rows):\n{json.dumps(sample_data[:5], indent=2)}\n"

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text.strip()
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            # Strip markdown fences if present
            cleaned = raw_text
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned.strip())

        rules: list[TransformationRule] = []
        for item in parsed:
            rule_type_str = item.get("rule_type", "DIRECT_MAP")
            try:
                rule_type = TransformationRuleType(rule_type_str)
            except ValueError:
                rule_type = TransformationRuleType.CUSTOM

            rules.append(
                TransformationRule(
                    source_field=item.get("source_field", ""),
                    target_field=item.get("target_field", ""),
                    rule_type=rule_type,
                    rule_expression=item.get("rule_expression", ""),
                    description=item.get("description", ""),
                )
            )

        return rules
