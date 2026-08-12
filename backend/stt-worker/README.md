# stt_worker

Background consumer: reads `stt.jobs` off RabbitMQ (published by `feedback` when a
submission includes `audio_file`), transcribes/analyzes it, and writes the result back
to `database` via its internal `PATCH /feedback/{id}/processing` endpoint. No public API
surface beyond `/health` — everything else happens off the queue. Talks to `database`
over HTTP; owns no DB tables itself. Reads audio from the same volume `feedback` writes
to (`AUDIO_STORAGE_DIR`, shared via the `feedback_audio` compose volume).

## STT backend

`src/stt_worker/stt_client.py` is the one integration seam: `transcribe(audio_path)`
submits the audio file to the muxlisa async STT microservice
(`STT_BASE_URL`, default `https://service.muxlisa.uz/api/v1`), then polls
`/async/stt/status/{task_id}` until the task reaches `COMPLETED` and returns the plain
transcript string. Requires `STT_API_KEY` to be set; without it jobs fail fast
(`processing_status` -> `failed`) with a clear log line instead of hanging.

The transcript is PATCHed back to `database` as `transcript` + `processing_status: "done"`
(sentiment/keywords no longer come from the STT client).

Env vars:

- `STT_BASE_URL` — base URL of the muxlisa STT service (default `https://service.muxlisa.uz/api/v1`)
- `STT_API_KEY` — API key sent as `x-api-key`
- `STT_POLL_INTERVAL_SECONDS` — delay between status polls (default `2`)
- `STT_POLL_TIMEOUT_SECONDS` — max time to wait for completion (default `60`)
