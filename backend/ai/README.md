# ai

AI chatbot service. Two endpoints, both stateless — no chat history stored anywhere
(no conversation table, `conversation_id` is only echoed back to the caller for
client-side threading).

## Endpoints

- `POST /api/ai/chat` — `{message, conversation_id?, user_geo?}` -> LLM reply.
- `POST /api/ai/chat/audio` — multipart `audio` file (+ optional `conversation_id`,
  `user_geo` form fields) -> transcript only (STT result, in-memory). Client renders
  the transcript as the user's message, then sends that text to `POST /api/ai/chat`
  to get the AI reply.

## LLM backend

`src/ai/llm_client.py` calls an OpenAI-compatible chat-completions endpoint —
currently Qwen served by LM Studio at `LLM_BASE_URL` (default
`http://172.16.8.197:1234/v1`). Set `LLM_MODEL` to the exact model id LM Studio
reports at `GET /v1/models` if it differs from the default.

## STT backend

`src/ai/stt_client.py` submits audio to muxlisa's async STT API
(`STT_BASE_URL`, default `https://service.muxlisa.uz/api/v1`), then polls
`/async/stt/status/{task_id}` until `COMPLETED` (`STT_POLL_INTERVAL_SECONDS` /
`STT_POLL_TIMEOUT_SECONDS`). Requires `STT_API_KEY`.

## Env vars

- `DATABASE_SERVICE_URL` — for JWT auth user lookup only.
- `JWT_SECRET`
- `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`
- `STT_BASE_URL`, `STT_API_KEY`, `STT_POLL_INTERVAL_SECONDS`, `STT_POLL_TIMEOUT_SECONDS`
