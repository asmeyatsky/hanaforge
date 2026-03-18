"""ClaudeAgentExecutor — implements AgentExecutorPort using the Anthropic SDK tool-use API.

Runs an autonomous agent loop: send a message to Claude, receive tool_use blocks,
execute the requested tools, feed results back, and repeat until the model produces
a final text response or the step limit is reached.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import anthropic

from domain.entities.agent_task import AgentTask
from domain.services.agent_tool_registry import AgentToolRegistry
from domain.value_objects.agent_types import AgentResult, AgentStep, AgentTool

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an autonomous SAP S/4HANA migration agent running inside the HanaForge platform.

Your objective will be given in the first user message.  You have access to a set of
tools that let you inspect programme data, trigger analyses, check migration readiness,
and more.

Guidelines:
- Think step by step before choosing a tool.
- Call one tool at a time when the next step depends on the previous result.
- When you have gathered enough information to answer the objective, respond with
  a clear, structured summary.  Do NOT call another tool if you already have the answer.
- If a tool returns an error, try a different approach or report what went wrong.
- Be concise but thorough in your final answer.
"""


class ClaudeAgentExecutor:
    """Implements AgentExecutorPort by driving a Claude tool-use conversation loop."""

    def __init__(
        self,
        api_key: str,
        tool_registry: AgentToolRegistry,
        model: str = "claude-sonnet-4-20250514",
        max_concurrent_tools: int = 5,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._registry = tool_registry
        self._semaphore = asyncio.Semaphore(max_concurrent_tools)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_agent_loop(
        self,
        task: AgentTask,
        tools: list[AgentTool],
        max_steps: int = 20,
    ) -> AgentResult:
        """Run the full agent loop for the given task and available tools.

        Returns an AgentResult containing the final output, execution steps,
        and total token usage.
        """
        # Build the tool definitions for the Claude API
        api_tools = self._build_api_tools(tools)

        # Initialise the conversation
        messages: list[dict] = [
            {
                "role": "user",
                "content": self._build_initial_prompt(task),
            }
        ]

        steps: list[AgentStep] = []
        total_input_tokens = 0
        total_output_tokens = 0

        for step_num in range(1, max_steps + 1):
            logger.info(
                "Agent step %d/%d for task %s",
                step_num,
                max_steps,
                task.id,
            )

            # Call Claude
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                tools=api_tools,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            # Process response content blocks
            if response.stop_reason == "end_turn":
                # Model produced a final text answer
                final_text = self._extract_text(response)
                step = AgentStep(
                    thought=final_text,
                    tool_name=None,
                    tool_input=None,
                    tool_output=None,
                    timestamp=datetime.now(timezone.utc),
                )
                steps.append(step)
                logger.info(
                    "Agent completed for task %s after %d steps",
                    task.id,
                    step_num,
                )
                return AgentResult(
                    success=True,
                    output=final_text,
                    steps=tuple(steps),
                    tokens_used=total_input_tokens + total_output_tokens,
                )

            if response.stop_reason == "tool_use":
                # Extract thinking text and tool-use blocks
                thought_text = ""
                tool_use_blocks = []
                for block in response.content:
                    if block.type == "text":
                        thought_text += block.text
                    elif block.type == "tool_use":
                        tool_use_blocks.append(block)

                # Append assistant message to conversation
                messages.append({"role": "assistant", "content": response.content})

                # Execute each tool call and collect results
                tool_results = []
                for tool_block in tool_use_blocks:
                    tool_output = await self._execute_tool(tool_block.name, tool_block.input)
                    tool_output_str = json.dumps(tool_output, default=str)

                    step = AgentStep(
                        thought=thought_text,
                        tool_name=tool_block.name,
                        tool_input=tool_block.input,
                        tool_output=tool_output_str,
                        timestamp=datetime.now(timezone.utc),
                    )
                    steps.append(step)

                    logger.info(
                        "Agent tool call: %s (task %s, step %d)",
                        tool_block.name,
                        task.id,
                        step_num,
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": tool_output_str,
                        }
                    )

                # Feed tool results back to the conversation
                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason — extract whatever text is available
                final_text = self._extract_text(response)
                step = AgentStep(
                    thought=final_text or f"Unexpected stop_reason: {response.stop_reason}",
                    tool_name=None,
                    tool_input=None,
                    tool_output=None,
                    timestamp=datetime.now(timezone.utc),
                )
                steps.append(step)
                return AgentResult(
                    success=True,
                    output=final_text or "Agent ended unexpectedly.",
                    steps=tuple(steps),
                    tokens_used=total_input_tokens + total_output_tokens,
                )

        # Exhausted max_steps
        logger.warning("Agent hit max_steps (%d) for task %s", max_steps, task.id)
        return AgentResult(
            success=False,
            output=f"Agent reached the maximum of {max_steps} steps without completing.",
            steps=tuple(steps),
            tokens_used=total_input_tokens + total_output_tokens,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_initial_prompt(self, task: AgentTask) -> str:
        """Build the initial user message from the task objective and context."""
        parts = [f"## Objective\n{task.objective}"]
        if task.context:
            parts.append(f"\n## Context\n```json\n{json.dumps(task.context, indent=2, default=str)}\n```")
        return "\n".join(parts)

    @staticmethod
    def _build_api_tools(tools: list[AgentTool]) -> list[dict]:
        """Convert AgentTool descriptors into the Anthropic API tool format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in tools
        ]

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        """Extract concatenated text from all text blocks in a response."""
        parts = []
        for block in response.content:
            if block.type == "text":
                parts.append(block.text)
        return "\n".join(parts)

    async def _execute_tool(self, name: str, params: dict) -> dict:
        """Execute a tool through the registry with concurrency control."""
        async with self._semaphore:
            try:
                return await self._registry.execute(name, params)
            except Exception as exc:
                logger.error("Tool %s failed: %s", name, exc)
                return {"error": str(exc)}
