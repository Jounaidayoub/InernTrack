#!/usr/bin/bash

backup_database() {
  local output_file="$1"

  if [[ ! -f "$SQLITE_DB_PATH" ]]; then
    echo "[ERROR] SQLite database not found: $SQLITE_DB_PATH"
    exit 1
  fi

  # Safe for most workloads; replace with sqlite3 .backup if needed
  cp "$SQLITE_DB_PATH" "$output_file"
}
