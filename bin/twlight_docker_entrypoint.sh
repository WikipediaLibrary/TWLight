#!/usr/bin/env bash
set -euo pipefail
source /app/bin/virtualenv_activate.sh
exec "${@}"
