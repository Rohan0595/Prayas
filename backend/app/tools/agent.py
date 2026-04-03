"""
Agent loop — orchestrates multi-step reasoning with tool use.

Flow:
  1. Send messages to LLM with tool definitions
  2. If LLM returns tool_call → execute tool → append result → loop
  3. If LLM returns text → done
  4. Cap iterations to prevent runaway loops
"""
import json
from typing import List, Dict, Optional
from app.models.openrouter import openrouter_client
from app.tools.executor import TOOL_DEFINITIONS, execute_tool
from app.core.config import settings


async def run_agent(
    messages: List[Dict[str, str]],
    model: str,
    system_prompt: str = "",
) -> str:
    """
    Run the agent loop and return the final text response.
    Uses non-streaming completions so we can inspect tool calls.
    """
    # Prepend system prompt if provided
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    for iteration in range(settings.MAX_AGENT_ITERATIONS):
        response = await openrouter_client.chat_completion(
            model=model,
            messages=full_messages,
            tools=TOOL_DEFINITIONS,
        )

        choice = response["choices"][0]
        message = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")

        # ── Terminal: model produced a text response ──
        if finish_reason == "stop" or not message.get("tool_calls"):
            return message.get("content", "")

        # ── Tool use: execute each requested tool ──
        full_messages.append(message)  # append assistant's tool-call message

        for tool_call in message["tool_calls"]:
            fn_name = tool_call["function"]["name"]
            try:
                fn_args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}

            tool_result = execute_tool(fn_name, fn_args)

            # Append tool result in the format expected by the API
            full_messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": tool_result,
            })

    # Max iterations reached — ask for a final answer without tools
    full_messages.append({
        "role": "user",
        "content": "Please provide your final answer based on the information gathered so far.",
    })
    final = await openrouter_client.chat_completion(
        model=model,
        messages=full_messages,
    )
    return final["choices"][0]["message"].get("content", "I was unable to complete this task.")
