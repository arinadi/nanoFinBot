# Gemini via OpenAI-compatible endpoint — reference

Gemini models are reachable through the same OpenAI SDK using these base URLs and
`model` names (confirm the exact model id against Google's current docs at build time).

**Gemini API (AI Studio key)** — base URL:
```
https://generativelanguage.googleapis.com/v1beta/openai/
```
`api_key` = the Gemini API key; `model` e.g. `gemini-2.5-flash`.

**Vertex AI (Google Cloud project)** — base URL:
```
https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{location}/endpoints/openapi
```
`api_key` = a Google Cloud access token (OAuth); `model` = `google/{model_id}`.

**What this means for nanoFinBot**: nothing Gemini-specific is coded. The user pastes
the base URL, key, and model into `config.json` (via `nfb setup` or the bot UI), and the
single `provider.py` client calls it. This satisfies the "OpenAI support API" requirement
without a second SDK.

**OCR cost note** (from Phase 0 research): Gemini vision is token-billed and output
tokens dominate; downscale images to ≤768px before sending (see `reference/pillow.md`)
to keep the image to a single 258-token tile.
