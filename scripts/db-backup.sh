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

log "Uploading ${DB_NAME} to s3://${S3_BUCKET_NAME}/${DB_DUMP_S3_PREFIX}/${DB_DUMP_FILENAME_WITH_TIMESTAMP}.gz"
mysqldump -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASS}" -B "${DB_NAME}" | gzip -9 | s3cmd --config .s3cfg put - "s3://${S3_BUCKET_NAME}/${DB_DUMP_S3_PREFIX}/${DB_DUMP_FILENAME_WITH_TIMESTAMP}.gz"
