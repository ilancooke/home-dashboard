#!/usr/bin/env bash

# Update the deployed checkout, install dependencies, and restart the service.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

git pull
.venv/bin/pip install -r requirements.txt
systemctl restart home-dashboard
systemctl --no-pager --full status home-dashboard
