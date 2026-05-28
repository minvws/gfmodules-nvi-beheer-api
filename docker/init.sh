#!/usr/bin/env bash

set -e

APP_PATH="${FASTAPI_CONFIG_PATH:-app.conf}"

echo "➡️ Creating the configuration file"
if [ -e $APP_PATH ]; then
  echo "⚠️ Configuration file already exists. Skipping."
else
  cp app.conf.example $APP_PATH
fi

echo "Migrating"
DSN=$(grep dsn $APP_PATH | sed -r 's/dsn=postgresql\+psycopg/postgresql/' ) tools/./migrate_db.sh

echo "Start main process"
python -m app.main
