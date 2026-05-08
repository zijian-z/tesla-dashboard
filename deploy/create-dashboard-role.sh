#!/bin/sh
set -eu

: "${POSTGRES_USER:=teslamate}"
: "${POSTGRES_HOST:=database}"
: "${POSTGRES_DB:=teslamate}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${DASHBOARD_DB_USER:=dashboard_readonly}"
: "${DASHBOARD_DB_PASSWORD:?DASHBOARD_DB_PASSWORD is required}"

export PGPASSWORD="$POSTGRES_PASSWORD"

echo "Waiting for PostgreSQL at $POSTGRES_HOST..."
until pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  sleep 1
done

echo "Creating or updating read-only dashboard role: $DASHBOARD_DB_USER"
psql \
  -h "$POSTGRES_HOST" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 \
  -v dashboard_user="$DASHBOARD_DB_USER" \
  -v dashboard_password="$DASHBOARD_DB_PASSWORD" <<'SQL'
select set_config('dashboard.user', :'dashboard_user', false);
select set_config('dashboard.password', :'dashboard_password', false);

do $$
declare
  dashboard_user text := current_setting('dashboard.user');
  dashboard_password text := current_setting('dashboard.password');
begin
  if not exists (select 1 from pg_roles where rolname = dashboard_user) then
    execute format('create role %I login password %L', dashboard_user, dashboard_password);
  else
    execute format('alter role %I with login password %L', dashboard_user, dashboard_password);
  end if;

  execute format('grant connect on database %I to %I', current_database(), dashboard_user);
  execute format('grant usage on schema public to %I', dashboard_user);
  execute format('grant select on all tables in schema public to %I', dashboard_user);
  execute format('grant select on all sequences in schema public to %I', dashboard_user);
  execute format('alter default privileges for role %I in schema public grant select on tables to %I', current_user, dashboard_user);
  execute format('alter role %I set default_transaction_read_only = on', dashboard_user);
  execute format('alter role %I set statement_timeout = %L', dashboard_user, '15s');

  begin
    execute format('revoke all on schema private from %I', dashboard_user);
  exception
    when invalid_schema_name then
      null;
  end;
end
$$;
SQL

echo "Read-only dashboard role is ready: $DASHBOARD_DB_USER"
