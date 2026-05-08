#!/bin/sh
set -eu

BASIC_AUTH_USER="${BASIC_AUTH_USER:-admin}"
BASIC_AUTH_PASSWORD="${BASIC_AUTH_PASSWORD:-change-me}"

if [ "$BASIC_AUTH_PASSWORD" = "change-me" ]; then
  echo "WARN: BASIC_AUTH_PASSWORD is still set to the default value."
fi

HASH="$(openssl passwd -apr1 "$BASIC_AUTH_PASSWORD")"
printf "%s:%s\n" "$BASIC_AUTH_USER" "$HASH" > /etc/nginx/.htpasswd
chmod 644 /etc/nginx/.htpasswd
