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

BACKUP_TO_RESTORE="${1:-}"

if [ "${BACKUP_TO_RESTORE}" = "--help"  ] || [ "${BACKUP_TO_RESTORE}" = "-h" ]
then
    echo "Usage: ${0} <backup_to_restore>.sql.gz"
    echo "Can be found with 's3cmd --config .s3cfg ls s3://${S3_BUCKET_NAME}/${DB_DUMP_S3_PREFIX}/'"
    exit 1
fi

if [ -z "${BACKUP_TO_RESTORE}" ]
then
    # List the bucket contents, filter out the directories, sort by time with newest first, take the first one, return only the s3 path
    BACKUP_TO_RESTORE=$(s3cmd --config .s3cfg ls "s3://${S3_BUCKET_NAME}/${DB_DUMP_S3_PREFIX}/" | grep -v DIR | sort -rnk2 | head -1 | awk '{ print $4 }')
    log "No backup specified, using one of today's backups: ${BACKUP_TO_RESTORE}"
fi

log "Downloading ${BACKUP_TO_RESTORE} to ${DB_DUMP_FILENAME_WITH_TIMESTAMP}"
s3cmd --config .s3cfg --no-progress get "${BACKUP_TO_RESTORE}" - | gunzip > "${DB_DUMP_FILENAME_WITH_TIMESTAMP}"

log "Dropping database ${DB_NAME}"
mysql -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASS}" <<< "DROP DATABASE IF EXISTS FoD;"
log "Creating database ${DB_NAME}"
mysql -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASS}" <<< "create database FoD;"
log "Restoring database ${DB_NAME} from ${DB_DUMP_FILENAME_WITH_TIMESTAMP}"
mysql -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASS}" "${DB_NAME}" < "${DB_DUMP_FILENAME_WITH_TIMESTAMP}"
