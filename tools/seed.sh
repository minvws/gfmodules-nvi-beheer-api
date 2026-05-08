#!/usr/bin/env bash
set -euo pipefail

echo "Seeding some test healthcare providers..."

psql postgresql://postgres:postgres@localhost:5432/postgres <<'SQL'
INSERT INTO healthcare_providers (id, ura_number, is_source, is_viewer, source_id, oin, common_name, status)
VALUES
    ('a1b2c3d4-0001-0001-0001-000000000001', '10000001', true,  false, 'src-001', '00000001000000000001', 'Ziekenhuis',    'active'),
    ('a1b2c3d4-0002-0002-0002-000000000002', '10000002', false, true,  'src-002', '00000001000000000002', 'Huisartsenpraktijk', 'active'),
    ('a1b2c3d4-0003-0003-0003-000000000003', '10000003', true,  true,  'src-003', '00000001000000000003', 'GGD',           'soft-freeze'),
    ('a1b2c3d4-0004-0004-0004-000000000004', '10000004', false, true,  'src-004', '00000001000000000004', 'Apotheek',       'suspended'),
    ('a1b2c3d4-0005-0005-0005-000000000005', '10000005', true,  false, 'src-005', '00000001000000000005', 'Revalidatiecentrum', 'hard-blocked'),
    ('a1b2c3d4-0006-0006-0006-000000000006', '10000006', true,  false, 'src-006', '00000001000000000006', 'Crisiscentrum', 'hard-blocked')
ON CONFLICT (id) DO NOTHING;
SQL
