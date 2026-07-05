# Personal Finance Coach 💸

![Cover Banner](assets/cover_page_banner.png)

An intelligent multi-agent AI assistant built with Google Agent Development Kit (ADK) to help you manage your finances, create budgets, and optimize your savings strategies.

## Features

![Architecture Diagram](assets/architecture_diagram.png)

- **Multi-Agent Architecture**: 
  - 🧠 **Orchestrator**: Routes user queries to specialized agents.
  - 📊 **Budget Advisor**: Analyzes spending and helps you set up structured budgets.
  - 💰 **Savings Advisor**: Provides strategies for compound interest, goals, and safe savings rates.
- **Human-in-the-Loop (HITL)**: Budget proposals automatically pause the workflow and request human approval before finalizing.
- **Security Checkpoint**: Intercepts all inputs to scrub PII (Credit Cards, SSNs) and detect prompt injection attempts, logging events to an audit trail.
- **MCP Integration**: Uses the Model Context Protocol (MCP) to provide agents with tools to interact with the local filesystem and external data sources.

## Getting Started

### Prerequisites
- Python 3.11+
- `uv` package manager
- Gemini API Key

### Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Environment Variables:**
   Ensure you have your Gemini API key in the `.env` file at the root of the workspace:
   ```env
   GEMINI_API_KEY=your_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

### Running the Application

Start the interactive ADK web playground:

**Windows:**
```powershell
uv run adk web app --host 127.0.0.1 --port 18081 --reload_agents
```

**macOS / Linux:**
```bash
make playground
```

Open your browser to `http://127.0.0.1:18081` to chat with your Personal Finance Coach!

### Running the MCP Server
The project includes a FastMCP server that exposes tools to the agents.
```bash
make mcp
```

## Development

- **Linting**: `make lint`
- **Formatting**: `make format` (or `uv run ruff format .`)
- **Testing**: `make test`
