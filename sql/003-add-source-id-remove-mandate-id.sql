
DROP INDEX IF EXISTS uq_clients_org_mandate_active;

ALTER TABLE clients
	DROP COLUMN mandate_id,
	ADD COLUMN source_id VARCHAR;

CREATE UNIQUE INDEX uq_clients_org_oin_cn_active
	ON clients (organization_id, oin, common_name)
	WHERE deleted_at IS NULL;

-- Migrate data from healthcare_providers to orgs and clients
-- Create one organization per unique ura_number
WITH unique_uras AS (
  SELECT DISTINCT ura_number
  FROM healthcare_providers
)
INSERT INTO organizations (id, register_id, name, scopes, created_at, deleted_at)
SELECT gen_random_uuid(), ura_number, ura_number, 'nvi:create nvi:read nvi:update nvi:delete nvi:localize', now(), NULL
FROM unique_uras;

-- Create clients for each healthcare_provider
INSERT INTO clients (id, organization_id, oin, common_name, source_id, scopes, created_at, deleted_at)
SELECT hp.id, org.id, hp.oin, hp.common_name, hp.source_id,
  CASE 
    WHEN hp.is_source THEN 'nvi:create nvi:read nvi:update nvi:delete'
    WHEN hp.is_viewer THEN 'nvi:localize'
  END,
  now(),
  hp.deleted_at
FROM healthcare_providers hp
JOIN organizations org ON hp.ura_number = org.register_id;

DROP TABLE IF EXISTS healthcare_providers;