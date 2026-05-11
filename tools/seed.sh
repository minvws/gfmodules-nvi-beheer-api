#!/usr/bin/env bash
set -euo pipefail

echo "Seeding some test healthcare providers..."

psql postgresql://postgres:postgres@localhost:5432/postgres <<'SQL'
INSERT INTO healthcare_providers (id, ura_number, is_source, is_viewer, source_id, oin, common_name, status)
VALUES
    (gen_random_uuid(), '90000380', true,  false, 'src-001', '00000099000000001000', 'Ziekenhuis',    'active'),
    (gen_random_uuid(), '90000381', false, true,  'src-002', '00000099000000002000', 'Huisartsenpraktijk', 'active'),
    (gen_random_uuid(), '90000382', true,  true,  'src-003', '00000099000000003000', 'GGD',           'soft-freeze'),
    (gen_random_uuid(), '90000380', false, true,  'src-004', '00000099000000004000', 'Apotheek',       'suspended'),
    (gen_random_uuid(), '90000381', true,  false, 'src-005', '00000099000000005000', 'Revalidatiecentrum', 'hard-blocked'),
    (gen_random_uuid(), '90000382', true,  false, 'src-006', '00000099000000006000', 'Crisiscentrum', 'hard-blocked');
SQL
