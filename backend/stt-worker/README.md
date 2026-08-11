# stt_worker

Background consumer: reads `stt.jobs` off RabbitMQ (published by `feedback` when a
submission includes `audio_file`), transcribes/analyzes it, and writes the result back
to `database` via its internal `PATCH /feedback/{id}/processing` endpoint. No public API
surface beyond `/health` — everything else happens off the queue. Talks to `database`
over HTTP; owns no DB tables itself. Reads audio from the same volume `feedback` writes
to (`AUDIO_STORAGE_DIR`, shared via the `feedback_audio` compose volume).

## STT backend

`src/stt_worker/stt_client.py` is the one integration seam: `transcribe(audio_path)`
POSTs the file to `STT_API_URL` (external speech-to-text API, not built yet) and expects
back:

```json
{"transcript": "...", "sentiment": "positive|neutral|negative", "keywords": ["..."]}
```

Until `STT_API_URL` is set, jobs fail fast (`processing_status` -> `failed`) with a clear
log line instead of hanging — swap in the real call once that API exists.
