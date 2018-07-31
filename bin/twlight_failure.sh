#!/usr/bin/env bash

if [ -z "$1" ]; then
    exit 1;
fi

failed_cmd="$1"

# Report failed command via email.
echo "$failed_cmd failed. Please check the logs." | mail -s "task failed for $(hostname -f)" ${TWLIGHT_ERROR_MAILTO}
