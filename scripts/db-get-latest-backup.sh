#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'

function setupDotEnv() {
    if [ -f .env ]
    then
        set -o allexport; source .env; set +o allexport
    fi
}
setupDotEnv

# To get log messages, call this script with DEBUG=true
function log() {
  local message="${1}"
  local debug_set="${DEBUG:-false}"

  if [ "${debug_set}" = "false" ]; then
    return
  fi

  printf "%s: %s\n" "$(date --iso-8601=seconds)" "${message}" >&2
}

latest_directory=$(s3cmd --config .s3cfg ls "s3://${S3_BUCKET_NAME}/" | grep DIR | sort -rk2 | head -1 | awk '{print $2}')
latest_file=$(s3cmd --config .s3cfg ls "${latest_directory}" | grep -v DIR | sort -rnk2 | head -1 | awk '{ print $4 }')
echo "$latest_file"
