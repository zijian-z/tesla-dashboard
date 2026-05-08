-- Run this against the TeslaMate database as the teslamate owner or a PostgreSQL superuser.
-- Replace the password before executing.

create user dashboard_readonly with password 'replace-with-a-strong-password';

grant connect on database teslamate to dashboard_readonly;
grant usage on schema public to dashboard_readonly;
grant select on all tables in schema public to dashboard_readonly;
grant select on all sequences in schema public to dashboard_readonly;

alter default privileges for role teslamate in schema public
  grant select on tables to dashboard_readonly;

alter role dashboard_readonly set default_transaction_read_only = on;
alter role dashboard_readonly set statement_timeout = '15s';

-- Intentionally no grants on the private schema. Tesla API tokens remain inaccessible.
