# Home Dashboard

A lightweight wall-mounted home dashboard designed to run on an older tablet and be served from a homelab.

The initial target device is a 5th-generation Amazon Fire 7 with a 1024×600 landscape display.

The application is intentionally being built as a modular monolith: one deployable app with separate internal modules for weather, smart-home controls, music controls, and future integrations.

## Current Status

The first working module is weather.

Current functionality:

- Flask web application
- National Weather Service API integration
- Current conditions display
- Five-hour forecast with weather icons, temperature, wind speed, and precipitation chance
- Five-day forecast with weather icons, daily high/low temperatures, and precipitation chance
- Fullscreen button using the browser Fullscreen API when supported
- Automatic page refresh every 10 minutes
- Basic graceful handling of NWS API failures
- Layout optimized for a 1024×600 landscape display
- Space reserved for future dashboard modules

The app is currently developed locally on macOS and will be deployed to a Debian LXC container running on Proxmox.

## Intended Architecture

```text
                         ┌───────────────────────┐
                         │ External APIs         │
                         │                       │
                         │ NWS                   │
                         │ Home Assistant        │
                         │ Music / Stereo APIs   │
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
                         │   music.py            │
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
├── requirements.txt
├── modules/
│   ├── __init__.py
│   └── weather.py
├── templates/
│   └── index.html
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
│ Weather                                      │
│                                              │
│ Current temperature / conditions             │
│                                              │
│ Five-hour forecast  │  Five-day forecast     │
│ icon / temp / wind  │  icon / high / low     │
│ precipitation       │  precipitation          │
├──────────────────────────────────────────────┤
│                                              │
│ Reserved for future modules                  │
│                                              │
│ Home Assistant controls     Music controls   │
│                                              │
└──────────────────────────────────────────────┘
```

Do not build the Home Assistant or music modules yet unless explicitly requested.

The current priority is to establish a clean foundation and reliable deployment workflow.

The dashboard includes a visible Fullscreen button. It requests fullscreen for the
document root using the standard Fullscreen API and older vendor-prefixed variants
when available. Fullscreen behavior depends on the browser and Fire OS version.

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

The application should eventually run as a persistent service rather than using Flask's development server.

A likely deployment pattern is:

```text
Git repository
      ↓
Proxmox Debian LXC
      ↓
Python virtual environment
      ↓
Gunicorn or another WSGI server
      ↓
systemd service
      ↓
Fire tablet browser
```

The production server and service configuration have not yet been implemented.

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
9. Do not prematurely implement Home Assistant or music functionality.
10. Preserve the ability to add those modules cleanly later.

## Planned Future Work

Near-term:

- Commit the initial application to Git
- Deploy the application to the Proxmox LXC
- Run the application as a persistent system service
- Make the dashboard reachable from other devices on the LAN
- Load the dashboard from the Fire 7
- Configure the Fire for an always-on / kiosk-like display

Later:

- Improve weather presentation
- Add weather icons
- Add better daily high/low organization
- Add clock/date
- Integrate Home Assistant
- Add music-zone controls
- Potentially add indoor climate and device status
- Add navigation or modular dashboard views if needed

## Notes for Codex

Before making significant architectural changes, preserve the current direction:

- This is a home dashboard, not just a weather app.
- Weather is only the first module.
- The app should remain lightweight enough for an old Fire 7 browser.
- The production environment is a Proxmox-hosted Debian LXC.
- The target display resolution is 1024×600 landscape.
- The user prefers incremental development and does not want unrelated future modules implemented prematurely.
