#!/usr/bin/env bash
SECRET_KEY=twlight ./bin/twlight_static.sh
set -euo pipefail
source /app/bin/virtualenv_activate.sh
exec "${@}"
