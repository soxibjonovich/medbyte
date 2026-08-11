# feedback

Patient feedback intake service: multipart submission (rating, tags, text comment, audio),
owner/admin detail lookup, and admin listing/transcript access. Talks to `database` over
HTTP; owns no DB tables itself. Audio files are stored on local disk under
`AUDIO_STORAGE_DIR`; actual speech-to-text/sentiment processing is done by a separate
worker (not part of this repo yet) that calls `database`'s internal
`PATCH /feedback/{id}/processing` endpoint once done.
