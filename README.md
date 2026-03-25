# Artemis II Remote Config

This file is fetched by the Artemis II iOS app every 15 minutes.
Edit `config.json` to update the app's behavior without an App Store update.

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `arow_websocket_url` | `string?` | AROW WebSocket URL. Set to `null` before launch. |
| `arow_active` | `bool` | Flip to `true` when AROW telemetry is live. The app auto-connects. |
| `ephemeris_url` | `string?` | URL to the downloadable OEM ephemeris file from NASA. |
| `message` | `string?` | Optional banner message shown in the app. |

## When to update

1. **Before launch:** Keep defaults (`arow_active: false`)
2. **At T-0 + ~1 min:** Inspect network traffic on `nasa.gov/trackartemis`, find the WebSocket URL, then update:
   ```json
   {
     "arow_websocket_url": "wss://discovered-url-here",
     "arow_active": true,
     "ephemeris_url": null,
     "message": "AROW live — tracking Orion!"
   }
   ```
3. **When ephemeris is published:** Add the download URL from NASA's AROW page.

## Setup

1. Create a GitHub repo called `artemis2-config`
2. Push this `config.json` to the `main` branch
3. The app fetches from: `https://raw.githubusercontent.com/joachimgresslien/artemis2-config/main/config.json`
