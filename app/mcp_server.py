# ruff: noqa
import logging
from typing import Dict

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Personal Finance MCP Server")


@mcp.tool()
def calculate_monthly_savings(income: float, expenses: float) -> float:
    """Calculate the remaining cash at the end of the month.

    Args:
        income: Total monthly income.
        expenses: Total monthly expenses.
    """
    return income - expenses


@mcp.tool()
def get_budget_limit(category: str) -> float:
    """Retrieve the budget limit for a specific category.

    Args:
        category: The category name (e.g. 'housing', 'food', 'entertainment').
    """
    category_limits = {
        "housing": 2000.0,
        "food": 600.0,
        "entertainment": 300.0,
        "transportation": 400.0,
        "savings": 500.0,
    }
    return category_limits.get(category.lower(), 100.0)  # Default small limit


@mcp.tool()
def suggest_savings_plan(goal: str) -> str:
    """Provide template recommendations for a savings goal.

    Args:
        goal: The saving goal (e.g. 'emergency fund', 'vacation', 'house').
    """
    goal = goal.lower()
    if "emergency" in goal:
        return "Plan: Save 3-6 months of living expenses. Keep it in a high-yield savings account for liquidity."
    elif "vacation" in goal:
        return "Plan: Estimate the total cost, divide by the number of months until the trip, and set up an automatic monthly transfer."
    elif "house" in goal:
        return "Plan: Save for a 20% down payment to avoid PMI. Consider a mix of high-yield savings and short-term CDs."
    else:
        return "Plan: Start by saving 10% of your income automatically each month towards your goal."


if __name__ == "__main__":
    mcp.run()
