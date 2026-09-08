# Home Dashboard

A lightweight wall-mounted home dashboard designed to run on an older tablet and be served from a homelab.

The initial target device is a 5th-generation Amazon Fire 7 with a 1024×600 landscape display.

The application is intentionally being built as a modular monolith: one deployable app with separate internal modules for weather, whole-home audio, smart-home controls, and future integrations.

## Current Status

The working modules are weather, whole-home audio, and camera snapshots.

Current functionality:

- Flask web application
- National Weather Service API integration
- Current conditions display
- Five-hour forecast with weather icons, temperature, wind speed, and precipitation chance
- Five-day forecast with weather icons, daily high/low temperatures, and precipitation chance
- Fullscreen button using the browser Fullscreen API when supported
- Automatic weather refresh every 10 minutes without leaving fullscreen
- Persistent Weather / Whole-Home Audio / Cameras navigation that keeps fullscreen active
- Basic graceful handling of NWS API failures
- Layout optimized for a 1024×600 landscape display
- Six-zone Monoprice amplifier status and per-zone controls
- Thread-safe RS-232 communication with reconnect handling
- Responsive audio controls for desktop, phone, and tablet browsers
- JSON API for audio status, power, source, volume, and mute
- Five Frigate camera snapshots through the dashboard server
- Full-size, touch-selected camera snapshot view

The app is developed locally on a MacBook and deployed to a Debian LXC container running on Proxmox.

## Intended Architecture

```text
                         ┌───────────────────────┐
                         │ External APIs         │
                         │                       │
                         │ NWS                   │
                         │ Home Assistant        │
                         │ Monoprice amplifier   │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Home Dashboard        │
                         │ Flask application     │
                         │                       │
                         │ modules/              │
                         │   weather.py          │
                         │   home_assistant.py   │
                         │   audio/              │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Fire 7 Tablet         │
                         │ 1024×600 landscape    │
                         │ Browser / kiosk mode  │
                         └───────────────────────┘
```

The tablet should remain a relatively dumb client. API calls, parsing, integration logic, and most application behavior should run on the server.

## Project Structure

```text
home-dashboard/
├── app.py
├── deploy.sh
├── requirements.txt
├── modules/
│   ├── __init__.py
│   ├── cameras.py
│   ├── weather.py
│   └── audio/
│       ├── __init__.py
│       ├── config.py
│       ├── controller.py
│       ├── protocol.py
│       └── routes.py
├── templates/
│   ├── base.html
│   ├── cameras.html
│   ├── index.html
│   └── audio.html
├── static/
│   ├── dashboard.css
│   ├── dashboard.js
│   ├── audio.js
│   └── cameras.js
├── tests/
│   ├── test_audio_controller.py
│   ├── test_audio_protocol.py
│   ├── test_audio_routes.py
│   ├── test_cameras.py
│   └── test_dashboard_pages.py
├── .gitignore
└── README.md
```

## Weather Module

The weather module currently uses the U.S. National Weather Service API.

Configured forecast endpoints:

```text
https://api.weather.gov/gridpoints/PSR/164,64/forecast
https://api.weather.gov/gridpoints/PSR/164,64/forecast/hourly
```

The NWS grid is based on the configured dashboard location.

Current weather data shown includes:

- current temperature and conditions
- five hourly periods with weather icon, temperature, wind speed, and probability of precipitation
- five daily periods with weather icon, high/low temperatures, and probability of precipitation

Hourly timestamps are converted from ISO timestamps into a human-readable format such as:

```text
9 PM
10 PM
11 PM
12 AM
```

## Current UI Direction

The dashboard is designed for a 1024×600 landscape display.

Current layout concept:

```text
┌──────────────────────────────────────────────┐
│ Weather | Whole-Home Audio | Cameras Fullscreen │
├──────────────────────────────────────────────┤
│                                              │
│ Current temperature / conditions             │
│                                              │
│ Five-hour forecast  │  Five-day forecast     │
│ icon / temp / wind  │  icon / high / low     │
│ precipitation       │  precipitation          │
├──────────────────────────────────────────────┤
│                                              │
│ Reserved for future Home Assistant controls  │
│                                              │
└──────────────────────────────────────────────┘
```

Do not build the Home Assistant module yet unless explicitly requested.

The current priority is to establish a clean foundation and reliable deployment workflow.

The dashboard includes a visible Fullscreen button. It requests fullscreen for the
document root using the standard Fullscreen API and older vendor-prefixed variants
when available. Fullscreen behavior depends on the browser and Fire OS version.

The shared top bar switches between Weather, Whole-Home Audio, and Cameras,
highlighting the active view. A small JavaScript navigation layer replaces only the
view content,
keeping the same document and fullscreen session alive. The Fullscreen button is
available in both views and changes to Exit fullscreen while active. Browser Back
and Forward also switch views without reloading the document. Both `/` and `/audio`
remain directly accessible, with ordinary links as a fallback for browsers without
the required navigation APIs.

Weather refreshes in place every 10 minutes while its view is open, and is fetched
again when returning from audio. Failed navigation requests retain the current view
and show a retry message. Audio status polling and camera snapshot refreshes run
only while their views are open. Navigation and refresh use XMLHttpRequest without
a frontend framework.

## Cameras Module

The Cameras view shows Back Patio, Driveway, East Gate, Front Yard, and West Gate
as a three-column snapshot grid sized for the 1024×600 display. It refreshes visible
snapshots every eight seconds. Tapping a camera shows a larger continuously refreshed
snapshot; tap All cameras to return to the grid.

The dashboard server proxies Frigate images rather than giving the tablet direct
Frigate access. Its endpoint is `GET /api/cameras/<camera>/latest.jpg`; responses
are not cached. The configured camera identifiers are in `modules/cameras.py`.

By default the server uses `http://192.168.88.120:5000`. Set `FRIGATE_URL` to use a
different Frigate endpoint. `FRIGATE_API_TOKEN` adds a Bearer token to Frigate image
requests when an authenticated endpoint is configured.

This first version intentionally uses still images, not live video. Adding a selected
camera live stream is a later step after go2rtc is configured and tested with the
Fire 7 browser.

## Whole-Home Audio Module

The audio module controls a Monoprice MPR-6ZHMAUT / product 10761 amplifier over
RS-232. The FTDI USB serial adapter is available in production at `/dev/ttyUSB0`
and uses 9600 baud, 8 data bits, no parity, one stop bit, and carriage-return command
terminators.

`MonopriceController` owns one lazily opened serial connection. A shared
`threading.Lock` covers every complete command/response transaction so concurrent
web requests cannot interleave serial traffic. Serial failures close the stale
connection and trigger a reconnect attempt; later requests can reconnect after the
USB device reappears. Errors are returned through the API without crashing Flask.

Zone and source display names are configured in `modules/audio/config.py`. The
dashboard currently shows Lounge, Master Bathroom, Patio, and Living Room. Zones 5
and 6 remain available through the API but are omitted from the UI until needed.

Audio pages and API routes:

```text
GET  /audio
GET  /api/audio/zones
GET  /api/audio/zones/<zone>
POST /api/audio/zones/<zone>/power   {"on": true}
POST /api/audio/zones/<zone>/source  {"source": 1}
POST /api/audio/zones/<zone>/volume  {"volume": 15}
POST /api/audio/zones/<zone>/mute    {"muted": true}
```

Zones and sources range from 1 through 6. Volume ranges from 0 through 38. The
controller also supports the documented per-zone treble, bass, and balance commands,
although those controls are not currently exposed in the web UI.

Protocol references:

- [Official Monoprice 10761 manual](https://downloads.monoprice.com/files/manuals/10761_Manual_131209.pdf)
- [mpr-6zhmaut-api](https://github.com/jnewland/mpr-6zhmaut-api)
- [monoprice-multizone-interface](https://github.com/cbschuld/monoprice-multizone-interface)
- [pyxantech](https://github.com/rsnodgrass/pyxantech)

## Development

Create and activate a local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the development server:

```bash
python3 app.py
```

The Flask development server currently listens on:

```text
http://127.0.0.1:8080
```

Port 8080 is used locally. The development server binds to all network interfaces,
so a device on the same LAN can access the dashboard at:

```text
http://<Mac-LAN-IP>:8080
```

For example:

```text
http://192.168.88.165:8080
```

Flask currently runs with debug mode enabled during local development, so Python changes are automatically detected and the development server reloads.

The audio page can be developed locally without an amplifier. The serial port is
opened only when an audio API request is made, and the automated tests use a fake
serial transport rather than `/dev/ttyUSB0`.

Run the test suite with:

```bash
python3 -m unittest discover -v
```

## Deployment Target

The deployment target is a Debian 12 LXC container on Proxmox.

Initial container configuration:

- Debian 12
- 1 CPU core
- 512 MB RAM
- 512 MB swap
- 4 GB disk
- unprivileged LXC
- start at boot enabled

Python 3.11 is installed in the container.

The production application runs as a persistent systemd-managed Gunicorn service. The deployment pattern is:

```text
Git repository
      ↓
Proxmox Debian LXC
      ↓
Python virtual environment
      ↓
Gunicorn
      ↓
systemd service
      ↓
Fire tablet browser
```

The service is installed on the container as `home-dashboard.service`:

```ini
[Unit]
Description=Home Dashboard
After=network.target

[Service]
WorkingDirectory=/opt/home-dashboard
ExecStart=/opt/home-dashboard/.venv/bin/gunicorn --bind 0.0.0.0:8080 app:app
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

The application is served from `/opt/home-dashboard` at `192.168.88.161:8080` and
listens on all container network interfaces. `Restart=always` keeps the service
available after an unexpected exit, and `WantedBy=multi-user.target` enables it to
start at boot.

The current Gunicorn command uses its default single worker. Keep the audio-enabled
deployment to one Gunicorn worker because `threading.Lock` coordinates threads within
one process, not separate worker processes sharing the same serial device.

### Deploying Updates

On the LXC container, run the deployment script from the application checkout:

```bash
cd /opt/home-dashboard
./deploy.sh
```

The script pulls the latest Git changes, installs dependencies into the existing virtual environment, restarts `home-dashboard`, and prints the resulting service status. It stops immediately if any step fails.

## Design Principles

When extending this project:

1. Keep it as one deployable application unless there is a concrete reason to split services.
2. Keep integrations separated into modules.
3. Keep the tablet-side code lightweight.
4. Prefer server-side API calls over requiring the old Fire browser to interact directly with third-party APIs.
5. Optimize UI changes for 1024×600 landscape.
6. Use large, touch-friendly controls for future interactive modules.
7. Avoid unnecessary frontend frameworks or heavy dependencies.
8. Favor reliability and simplicity over architectural complexity.
9. Do not prematurely implement Home Assistant or unrelated integrations.
10. Preserve the ability to add future modules cleanly later.

## Planned Future Work

Near-term:

- Make the dashboard reachable from other devices on the LAN
- Load the dashboard from the Fire 7
- Configure the Fire for an always-on / kiosk-like display

Later:

- Improve weather presentation
- Add weather icons
- Add better daily high/low organization
- Add clock/date
- Integrate Home Assistant
- Rename audio zones and sources for the physical installation
- Potentially add indoor climate and device status
- Add navigation or modular dashboard views if needed

## Notes for Codex

Before making significant architectural changes, preserve the current direction:

- This is a home dashboard, not just a weather app.
- Weather and whole-home audio are the current modules.
- The app should remain lightweight enough for an old Fire 7 browser.
- The production environment is a Proxmox-hosted Debian LXC.
- Production audio uses `/dev/ttyUSB0` through one Gunicorn worker.
- The target display resolution is 1024×600 landscape.
- The user prefers incremental development and does not want unrelated future modules implemented prematurely.
