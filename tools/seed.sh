#!/usr/bin/env bash
set -euo pipefail

echo "Seeding some test healthcare providers..."

psql postgresql://postgres:postgres@localhost:5432/postgres <<'SQL'
BEGIN;

DELETE FROM clients WHERE organization_id IN (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '44444444-4444-4444-4444-444444444444',
    '55555555-5555-5555-5555-555555555555'
);
DELETE FROM organizations WHERE id IN (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '44444444-4444-4444-4444-444444444444',
    '55555555-5555-5555-5555-555555555555'
);

INSERT INTO organizations (id, register_id, name, scopes, deleted_at) VALUES
    ('11111111-1111-1111-1111-111111111111', '00000099000000001000', 'ORG1', 'read write delete', NULL),
    ('22222222-2222-2222-2222-222222222222', '00000099000000002000', 'ORG2', 'read write', NULL),
    ('33333333-3333-3333-3333-333333333333', '00000099000000003000', 'ORG3', 'read', NULL),
    ('44444444-4444-4444-4444-444444444444', '00000099000000004000', 'ORG4', NULL, NULL),
    ('55555555-5555-5555-5555-555555555555', '00000099000000005000', 'ORG5', 'read write', now());

INSERT INTO clients (id, organization_id, mandate_id, oin, common_name, scopes, deleted_at) VALUES
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', '00000099000000001000',    '00000099000000002000', 'client.a.example.nl',  'read write', NULL),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', '12345678:device-001',     '00000099000000003000', 'client.b.example.nl',  'read',       NULL),
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', '00000099000000002000',    '00000099000000004000', 'client.c.example.nl',  'read write', NULL),
    (gen_random_uuid(), '33333333-3333-3333-3333-333333333333', '00000099000000003000',    '00000099000000005000', 'client.d.example.nl',  'read',       NULL),
    (gen_random_uuid(), '33333333-3333-3333-3333-333333333333', '12345678:device-009',     '00000099000000001000', 'client.e.example.nl',  'read',       now());

COMMIT;
SQL

echo "Done seeding 5 organizations and 5 clients."
