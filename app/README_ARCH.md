# Extended Architecture

- **session/** rolls up long chats into summaries.
- **knowledge/** retrieves learned chunks (RAG).
- **orchestrator/** picks model style (fast vs heavy).
- **plugins/** integrations (web search, music).
- **prompts/** versioned prompt files.
- **safety/** content & tool guardrails.
- **telemetry/** JSONL metrics.
- **eval/** quick offline checks.
- **infra/** cache + rate-limit.
- **configs/** config files.

Use them incrementally—wire session summarizer and knowledge grounder into your Thinker/Agent for immediate gains.
