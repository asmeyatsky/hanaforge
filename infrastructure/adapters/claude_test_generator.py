"""ClaudeTestGeneratorAdapter — implements TestGeneratorPort using the Anthropic SDK.

Sends SAP business process definitions to Claude with deep SAP domain knowledge
to generate structured, S/4HANA-specific test scenarios.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import anthropic

from domain.entities.test_scenario import TestScenario
from domain.value_objects.test_types import (
    ProcessArea,
    TestPriority,
    TestStatus,
    TestStep,
)

_SYSTEM_PROMPT = """\
You are an SAP S/4HANA test generation expert with deep knowledge of SAP business
processes and Fiori applications.

Your task is to generate structured end-to-end test scenarios for SAP business
processes in the target S/4HANA system.

Key SAP process knowledge you apply:

ORDER TO CASH (OTC):
- VA01 Create Sales Order, VA02 Change Sales Order, VL01N Delivery, VF01 Billing
- Fiori Apps: F0842 (Create Sales Order), F2680 (Manage Sales Orders)
- Credit management, pricing, availability check, output determination

PROCURE TO PAY (P2P):
- ME21N Create Purchase Order, MIGO Goods Receipt, MIRO Invoice Verification
- Fiori Apps: F0842A (Create Purchase Order), F2229 (Manage Purchase Orders)
- Source determination, approval workflows, GR/IR clearing

RECORD TO REPORT (RTR):
- FB01 Post Document, F-02 General Posting, FAGL_FC_VALUATION Foreign Currency
- Fiori Apps: F0717 (Post General Journal Entry), F2548 (Manage Journal Entries)
- New G/L, universal journal (ACDOCA), closing cockpit

HIRE TO RETIRE (H2R):
- PA30 Maintain HR Master, PA40 Personnel Actions, PT01 Time Management
- Fiori Apps: F6790 (My Paystubs), F1643 (Approve Leave Requests)
- Employee Central integration, SuccessFactors connectivity

PLAN TO PRODUCE (P2P):
- MD01 MRP Run, CO01 Create Production Order, MFBF Process Order
- Fiori Apps: F3808 (Manage Production Orders), F1984 (MRP Monitor)
- Demand management, capacity planning, shop floor integration

For each process area, generate test scenarios with:
1. Clear preconditions
2. Numbered test steps with actions and expected results
3. SAP transaction codes
4. Fiori app IDs for S/4HANA-specific tests
5. Appropriate priority levels
6. Meaningful tags

Return your response as a JSON array where each element follows this schema:
{
  "scenario_name": "<name>",
  "description": "<description>",
  "preconditions": ["<precondition1>", ...],
  "steps": [
    {"action": "<action>", "expected_result": "<result>",
     "sap_transaction": "<tcode or null>", "test_data": "<data or null>"},
    ...
  ],
  "expected_outcome": "<overall expected outcome>",
  "sap_transaction": "<primary tcode or null>",
  "fiori_app_id": "<Fiori app ID or null>",
  "priority": "CRITICAL|HIGH|MEDIUM|LOW",
  "tags": ["<tag1>", ...]
}

Return ONLY the JSON array, no markdown fences or additional text.
"""


class ClaudeTestGeneratorAdapter:
    """Implements TestGeneratorPort by sending process definitions to Claude."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate_test_scenarios(
        self,
        process_area: ProcessArea,
        process_definitions: list[dict],
        sap_version: str,
    ) -> list[TestScenario]:
        process_summary = json.dumps(process_definitions, indent=2)

        user_message = (
            f"Generate end-to-end test scenarios for the {process_area.value} "
            f"process area in SAP {sap_version}.\n\n"
            f"Business process definitions:\n{process_summary}\n\n"
            f"Generate comprehensive test scenarios covering happy path, "
            f"error handling, and edge cases."
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=8192,
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
            # Strip markdown fences if present
            cleaned = raw_text
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned.strip())

        now = datetime.now(timezone.utc)
        scenarios: list[TestScenario] = []

        for item in parsed:
            steps_raw = item.get("steps", [])
            steps = tuple(
                TestStep(
                    step_number=i + 1,
                    action=s.get("action", ""),
                    expected_result=s.get("expected_result", ""),
                    sap_transaction=s.get("sap_transaction"),
                    test_data=s.get("test_data"),
                )
                for i, s in enumerate(steps_raw)
            )

            scenario = TestScenario(
                id=str(uuid.uuid4()),
                programme_id="",  # Set by the use case caller
                process_area=process_area,
                scenario_name=item.get("scenario_name", "Unnamed"),
                description=item.get("description", ""),
                preconditions=tuple(item.get("preconditions", [])),
                steps=steps,
                expected_outcome=item.get("expected_outcome", ""),
                sap_transaction=item.get("sap_transaction"),
                fiori_app_id=item.get("fiori_app_id"),
                priority=TestPriority(item.get("priority", "MEDIUM")),
                status=TestStatus.DRAFT,
                tags=tuple(item.get("tags", [])),
                created_at=now,
            )
            scenarios.append(scenario)

        return scenarios
