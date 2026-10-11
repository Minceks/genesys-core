# OpenAI backend provider

Set `OPENAI_API_KEY` on the backend only. Select `GENESYS_PROVIDER=openai`,
`GENESYS_OPENAI_MODEL=gpt-5-mini`, and `GENESYS_FALLBACK_PROVIDER=gemini`.
The model is configurable; choose one with Chat Completions and function calling support.
Calls have a 60-second timeout and no SDK retries; the orchestrator handles bounded provider fallback.
Source context and current phase tool restrictions are preserved on provider changes.
Keys must never use VITE prefixes. This adds one provider to the existing autonomous job flow;
parallel builders are a separate feature. No live OpenAI generation check has been performed.
