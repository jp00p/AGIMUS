#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'

function setupDotEnv() {
  local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local env_path="${script_dir}/../.env"

  if [ -f "$env_path" ]; then
    set -o allexport
    source "$env_path"
    set +o allexport
  else
    echo "❌ .env file not found at $env_path"
    exit 1
  fi
}
setupDotEnv

DB_DUMP_FILENAME_WITH_TIMESTAMP="${DB_DUMP_FILENAME}-$(date +%s).sql"

# To get log messages, call this script with DEBUG=true
function log() {
  local message="${1}"
  local debug_set="${DEBUG:-false}"

  if [ "${debug_set}" = "false" ]; then
    return
  fi

  printf "%s: %s\n" "$(date --iso-8601=seconds)" "${message}" >&2
}

BACKUP_TO_RESTORE="${1:-}"
LOCAL_BACKUP_FILE=""

if [[ "$BACKUP_TO_RESTORE" == "--help" || "$BACKUP_TO_RESTORE" == "-h" ]]; then
  echo "Usage:"
  echo "  $0 s3://bucket/path/to/backup.sql.gz       # Restore from S3"
  echo "  $0 --file ./path/to/local_backup.sql.gz    # Restore from local file"
  exit 0
fi

if [[ "$BACKUP_TO_RESTORE" == "--file" ]]; then
  LOCAL_BACKUP_FILE="${2:-}"
  if [[ -z "$LOCAL_BACKUP_FILE" || ! -f "$LOCAL_BACKUP_FILE" ]]; then
    echo "❌ Please provide a valid path to a .sql.gz file"
    exit 1
  fi
  log "Using local backup file: $LOCAL_BACKUP_FILE"
  gunzip -c "$LOCAL_BACKUP_FILE" > "${DB_DUMP_FILENAME_WITH_TIMESTAMP}"
else
  if [ -z "${BACKUP_TO_RESTORE}" ]; then
    BACKUP_TO_RESTORE=$(s3cmd --config .s3cfg ls "s3://${S3_BUCKET_NAME}/${DB_DUMP_S3_PREFIX}/" | grep -v DIR | sort -rnk2 | head -1 | awk '{ print $4 }')
    log "No backup specified, using one of today's backups: $BACKUP_TO_RESTORE"
  fi

  log "Downloading ${BACKUP_TO_RESTORE} to ${DB_DUMP_FILENAME_WITH_TIMESTAMP}"
  s3cmd --config .s3cfg --no-progress get "${BACKUP_TO_RESTORE}" - | gunzip > "${DB_DUMP_FILENAME_WITH_TIMESTAMP}"
fi

log "Dropping database ${DB_NAME}"
mysql -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASS}" <<< "DROP DATABASE IF EXISTS FoD;"
log "Creating database ${DB_NAME}"
mysql -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASS}" <<< "create database FoD;"
log "Restoring database ${DB_NAME} from ${DB_DUMP_FILENAME_WITH_TIMESTAMP}"
mysql -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASS}" "${DB_NAME}" < "${DB_DUMP_FILENAME_WITH_TIMESTAMP}"
