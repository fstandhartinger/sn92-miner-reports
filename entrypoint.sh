#!/bin/sh
# Decrypt the report bundle (key only in the app's write-only env REPORTS_KEY) and serve it.
set -e
mkdir -p /srv/r
if [ -n "$REPORTS_KEY" ]; then
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:REPORTS_KEY -in /reports.tar.gz.enc | tar -xz -C /srv/r
else
  echo "REPORTS_KEY missing: serving no reports" >&2
fi
unset REPORTS_KEY
exec nginx -g 'daemon off;'
