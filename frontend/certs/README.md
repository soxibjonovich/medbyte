# Local HTTPS certs for Web Push (mobile testing)

Web Push (and browser Notifications) only work in a **secure context** (HTTPS or
`localhost`). Plain `http://<LAN-IP>:5173` is blocked on mobile, so the dev server
is configured to serve HTTPS when these two files exist:

- `key.pem` — private key
- `cert.pem` — self-signed certificate with `subjectAltName` for your LAN IP

## Regenerate (run from this directory)

```bash
LAN_IP=$(hostname -I | awk '{print $1}')
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 825 -nodes \
  -subj "/CN=$LAN_IP" \
  -addext "subjectAltName=IP:$LAN_IP,DNS:localhost,IP:127.0.0.1"
```

Then restart the dev server (`bun run dev`). Vite will now serve
`https://<LAN-IP>:5173`.

## Notes

- Browsers warn about the self-signed cert the first time — tap
  "Advanced → Proceed" on the phone once. After that the origin is treated as
  secure and push works.
- **iOS (Safari)**: Web Push only works for a web app **added to the Home
  Screen** (installed PWA), and only on iOS 16.4+. Android Chrome works without
  installing.
- These files are gitignored (see `frontend/.gitignore`).
