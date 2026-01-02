#!/usr/bin/bash
set -euo pipefail

# ==================================================
# CONFIGURATION
# ==================================================

DB_TYPE="sqlite"                  # sqlite | postgres | mysql (future)
DB_NAME="internships"

# SQLite specific
SQLITE_DB_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../data/internship_sync_new.db"

# Backup policy
ARCHIVE_RATE=10                   # keep N most recent backups
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="${DB_NAME}_${TIMESTAMP}.bak"

# Paths
BACKUP_ROOT="$(cd "$(dirname "$0")" && pwd)"
DUMP_DIR="$BACKUP_ROOT/dumps"
ARCHIVE_DIR="$BACKUP_ROOT/archives"
BACKENDS_DIR="$BACKUP_ROOT/backends"

# ==================================================
# INIT
# ==================================================

mkdir -p "$DUMP_DIR" "$ARCHIVE_DIR"

# ==================================================
# LOAD BACKEND
# ==================================================

BACKEND_FILE="$BACKENDS_DIR/${DB_TYPE}.sh"

if [[ ! -f "$BACKEND_FILE" ]]; then
  echo "[ERROR] Unsupported database type: $DB_TYPE"
  exit 1
fi

# shellcheck source=/dev/null
source "$BACKEND_FILE"

# ==================================================
# BACKUP
# ==================================================

echo "[INFO] Starting backup for database type: $DB_TYPE"
backup_database "$DUMP_DIR/$BACKUP_FILENAME"
echo "[OK] Backup created: $BACKUP_FILENAME"

# ==================================================
# ROTATION & ARCHIVING
# ==================================================

echo "[INFO] Checking for old backups to archive..."

OLD_BACKUPS=$(ls -1t "$DUMP_DIR" | tail -n +$((ARCHIVE_RATE + 1)) || true)

if [[ -n "$OLD_BACKUPS" ]]; then
  ARCHIVE_NAME="${DB_NAME}_archive_${TIMESTAMP}.tar.gz"

  tar -czf "$ARCHIVE_DIR/$ARCHIVE_NAME" -C "$DUMP_DIR" $OLD_BACKUPS
  rm -f $(printf "%s/%s\n" "$DUMP_DIR" $OLD_BACKUPS)

  echo "[OK] Archived old backups into: $ARCHIVE_NAME"
else
  echo "[INFO] No backups to archive"
fi

echo "[SUCCESS] Backup workflow completed"