# External integrations and local configuration

The redesign keeps external context out of the Bayesian crisis estimator. `weather.py`, `notifications.py`, and `twin_lab.py` add adapters and controlled demonstration endpoints; `inference.py`, `decision.py`, `voi.py`, `graph.py`, and their model configuration are unchanged.

## Public browser environment

The user-supplied public web configuration is in ignored `frontend/.env.local`. It is never displayed in the UI. Copy `frontend/.env.example` for another installation, supply the following values, and rebuild:

- `VITE_MAPTILER_KEY`
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `VITE_FIREBASE_VAPID_KEY`

Vite variables are public browser configuration, not a place for secrets. Firebase Analytics is not initialized; the supplied measurement ID is not needed for messaging. The public VAPID key alone cannot send push messages. Private service-account credentials must never use a `VITE_` prefix or appear in the frontend.

## MapTiler / MapLibre

The client uses MapLibre GL JS 6, an explicitly bundled module worker, and MapTiler dark and street vector styles. Its layers support pan/zoom, recentering, style switching, zone/sensor/infrastructure visibility and marker detail selection. Supported cities use approximate city-centre coordinates; all infrastructure and zone placements are explicitly illustrative.

The style endpoints were tested with the supplied public key and local-origin headers. Origin restrictions must be reviewed in the MapTiler account: the client key cannot read the account allowlist, and no deployed origin was supplied. Add the actual development origins used, such as `http://127.0.0.1:8000` and `http://localhost:5173`, and the eventual deployed HTTPS origin. Do not loosen the key to all origins merely to make a test pass.

Provider documentation: [MapLibre](https://maplibre.org/maplibre-gl-js/docs/) and [MapTiler](https://docs.maptiler.com/sdk-js/examples/switch-from-maplibre/).

## Open-Meteo

`GET /api/weather?location=nagpur` proxies current conditions and two days of hourly model estimates. Cities: Nagpur, Mumbai, Bengaluru, New Delhi, Kolkata. The backend caches each city for ten minutes, serializes overlapping requests, returns cached data during provider failures with an explicit stale status, and returns 503 when no prior response exists. The UI shows observation/model time, fetched time, provider attribution, temperature, precipitation/rain, humidity, wind, and hourly forecasts.

Weather is never submitted as a crisis observation. Hybrid places this context alongside a separately labeled simulated model. Live Observations hides simulated map overlays and simulated hazard assessments. The free endpoint is used for this non-commercial prototype; review [Open-Meteo terms](https://open-meteo.com/en/terms) before commercial deployment.

## Firebase Cloud Messaging

Implemented browser flow:

1. Check secure-context, Notification, service-worker, and Firebase SDK support.
2. Initialize only the Firebase products required for messaging.
3. Ask permission only after the user presses Enable test notifications.
4. Register the bundled `/firebase-messaging-sw.js`, obtain an FCM token with the supplied public VAPID key, and send it to the local backend.
5. Store token, random browser client ID, approximate simulated area, and opt-in time in SQLite. Status endpoints never return the token.
6. Handle foreground messages and service-worker background data messages. Notification clicks can open only a same-origin citizen page.
7. Opt-out removes the server registration and calls the Firebase token deletion API. OS/browser permission itself must be revoked through browser settings.

The worker is built from `frontend/worker/firebase-messaging-sw.ts`; it does not load Firebase from a third-party CDN. `npm run build` checks both app and worker types and bundles it. `npm run dev` builds the worker first. The API serves it as JavaScript at the site root.

### Missing trusted sender setup

The supplied configuration contains no server service-account credential. For actual FCM sends:

```sh
.venv/bin/python -m pip install -e './backend[notifications]'
export GOOGLE_APPLICATION_CREDENTIALS='/absolute/path/outside/repository/firebase-service-account.json'
export FIREBASE_PROJECT_ID='sentinel-zero-c95fb'
./run.sh
```

Use an account authorized to send FCM messages for that project. Keep the JSON outside this repository, do not paste it into the UI, and do not commit it. The SDK reads it server-side only when an opted-in browser requests a test send. The adapter sends data-only, clearly labeled test messages to that browser's registration; it does not broadcast emergency alerts.

`POST /api/notifications/test` returns 503 if trusted credentials or the optional server SDK are missing, 409 if the browser is not registered, and 502 with a bounded message if Firebase rejects the send. No raw SDK exception or token is returned. A successful response means FCM accepted the send, not proof of display or receipt.

### In-app observation requests

`POST /api/notifications/observation-request` creates a simulated request associated with the current random browser ID. `GET /api/notifications/requests` returns only requests for that ID. In-app requests work without push credentials; optional push is sent only when explicitly selected and the browser is opted in. Citizen responses use the existing `/api/citizen` path and evidence pipeline.

The local prototype has no production authentication. Random browser IDs isolate ordinary local UI use but are not a replacement for authenticated authorization or anti-abuse controls. Production deployment needs authenticated subscriptions, origin checks, rate limiting, secret management, and permission review.

Provider documentation: [FCM browser setup](https://firebase.google.com/docs/cloud-messaging/web/get-started), [message handling](https://firebase.google.com/docs/cloud-messaging/web/receive-messages), and [server sends](https://firebase.google.com/docs/cloud-messaging/send/admin-sdk).
