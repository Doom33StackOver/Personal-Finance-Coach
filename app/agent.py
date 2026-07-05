# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from google.adk.agents import Agent, LlmAgent, Context
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import AgentTool, ToolContext, McpToolset
from google.adk.workflow import Workflow, Edge, START, node
from google.adk.events.request_input import RequestInput
from google.genai import types
from mcp.client.stdio import StdioServerParameters

from app.config import config

# Setup shared model
llm_model = Gemini(
    model=config.model,
    retry_options=types.HttpRetryOptions(attempts=3),
)

# Initialize MCP Toolset
mcp_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="uv",
        args=["run", "python", "app/mcp_server.py"],
    )
)

# 1. Define Specialized Sub-Agents
budget_advisor = LlmAgent(
    name="budget_advisor",
    description="Specialist in analyzing expenses, budgeting rules (e.g. 50/30/20), and category allocation recommendations.",
    model=llm_model,
    instruction="""You are a Personal Budgeting Specialist.
Analyze the user's income and expenses. Propose a balanced budget.
You can recommend common rules like the 50/30/20 rule (50% needs, 30% wants, 20% savings) or custom category limits.
Provide clear, actionable budgeting tables and suggestions.
""",
    tools=[mcp_toolset],
)

savings_advisor = LlmAgent(
    name="savings_advisor",
    description="Specialist in recommending savings plans, emergency funds, and interest rate tips.",
    model=llm_model,
    instruction="""You are a Personal Savings Specialist.
Help the user build saving habits, create emergency funds, and define savings goals.
Provide compound interest estimates or savings timelines to motivate them.
""",
    tools=[mcp_toolset],
)


# 2. Define Custom Tools to interact with State
def propose_budget(ctx: ToolContext, proposed_budget_summary: str) -> str:
    """Flag that a new budget is proposed and requires human approval.

    Args:
        proposed_budget_summary: A short text summarizing the proposed budget structure.
    """
    return f"SYSTEM_NOTE: The budget has been recorded. You MUST include the exact string 'BUDGET_PROPOSAL_NEEDS_APPROVAL' in your final response to the user, followed by the budget summary: {proposed_budget_summary}"


# 3. Define Orchestrator coordinating sub-agents and tools
orchestrator = LlmAgent(
    name="orchestrator",
    description="Main entrypoint for coordinating finance advice",
    model=llm_model,
    instruction="""You are the Personal Finance Coach Orchestrator.
You are the primary point of contact for the user.
Your role is to understand the user's request and delegate to the appropriate specialized sub-agents:
- Use `budget_advisor` for requests about budgeting, expense analysis, and budget limits.
- Use `savings_advisor` for requests about saving strategies, goals, and interest/compounding.

If the user wants to set up or modify a budget, call the budget_advisor to generate a proposal, and then call the `propose_budget` tool.
IMPORTANT: If `propose_budget` tells you to include a string in your response, you MUST do it exactly as instructed.
""",
    tools=[
        AgentTool(budget_advisor),
        AgentTool(savings_advisor),
        propose_budget,
    ],
)

# 4. Define Workflow Nodes (including placeholders for Phase 4 Security)
import re
import json


@node(name="security_checkpoint")
def security_checkpoint(ctx: Context, node_input: Any) -> Any:
    input_str = str(node_input)

    # 1. Injection Detection
    forbidden_phrases = ["ignore previous", "disregard instructions", "system prompt"]
    if any(phrase in input_str.lower() for phrase in forbidden_phrases):
        ctx.route = "security_event"
        return "Injection detected."

    # 2. PII Scrubbing (Mask simple CC/SSN-like patterns)
    # Mask 16-digit credit cards
    scrubbed_input = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED CC]", input_str)
    # Mask SSN (AAA-GG-SSSS)
    scrubbed_input = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED SSN]", scrubbed_input)

    # 3. Audit Logging
    audit_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "original_input": input_str,
        "scrubbed_input": scrubbed_input,
        "action": "allow",
    }
    try:
        with open("audit.log", "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
    except Exception as e:
        print(f"Audit log error: {e}")

    ctx.route = "clean"
    return scrubbed_input


@node(name="security_error_node")
def security_error_node(ctx: Context, node_input: Any) -> str:
    # Audit log the failure
    audit_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "input": str(node_input),
        "action": "block",
        "reason": "security_policy_violation",
    }
    try:
        with open("audit.log", "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
    except Exception:
        pass
    return "Access denied due to a security policy violation."


@node(name="orchestrate", rerun_on_resume=True)
async def orchestrate(ctx: Context, node_input: Any) -> Any:
    # Run the orchestrator LlmAgent dynamically
    response = await ctx.run_node(orchestrator, node_input)

    response_str = str(response)
    ctx.state["orchestrator_output"] = response_str

    if "BUDGET_PROPOSAL_NEEDS_APPROVAL" in response_str:
        ctx.route = "needs_approval"
        ctx.state["needs_approval"] = True
        ctx.state["proposed_budget"] = response_str.replace(
            "BUDGET_PROPOSAL_NEEDS_APPROVAL", ""
        ).strip()
    else:
        ctx.state["needs_approval"] = False
        ctx.route = "direct_response"
    return response


@node(name="get_human_approval")
def get_human_approval(ctx: Context) -> Any:
    if not ctx.state.get("needs_approval"):
        return ctx.state.get("orchestrator_output", "No response.")

    # Resume check for HITL approval
    if ctx.resume_inputs and "approve_budget" in ctx.resume_inputs:
        user_resp = ctx.resume_inputs["approve_budget"]
        ctx.state["approved"] = user_resp.strip().lower() in ["yes", "approve"]
        ctx.state["needs_approval"] = False  # Clear flag

        if ctx.state["approved"]:
            return f"Thank you! The budget has been approved and saved.\n\nProposed Budget:\n{ctx.state.get('proposed_budget')}"
        else:
            return f"Budget was not approved. User feedback: {user_resp}"

    # Interrupt and request input
    return RequestInput(
        interruptId="approve_budget",
        message=f"Please review the proposed budget:\n\n{ctx.state.get('proposed_budget')}\n\nDo you approve? (Reply 'yes' to approve, or specify changes.)",
        responseSchema={"type": "string"},
    )


@node(name="final_output")
def final_output(ctx: Context, node_input: Any) -> Any:
    return node_input


# 5. Assemble the Workflow
finance_workflow = Workflow(
    name="finance_workflow",
    edges=[
        Edge(from_node=START, to_node=security_checkpoint),
        Edge(
            from_node=security_checkpoint,
            to_node=security_error_node,
            route="security_event",
        ),
        Edge(from_node=security_checkpoint, to_node=orchestrate, route="clean"),
        Edge(from_node=orchestrate, to_node=get_human_approval, route="needs_approval"),
        Edge(from_node=orchestrate, to_node=final_output, route="direct_response"),
        Edge(from_node=get_human_approval, to_node=final_output),
    ],
)

# Export root_agent and app for CLI/lifespan
root_agent = finance_workflow
app = App(
    name="app",
    root_agent=finance_workflow,
)
