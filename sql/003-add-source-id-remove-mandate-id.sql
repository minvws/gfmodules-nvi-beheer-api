DROP TABLE IF EXISTS healthcare_providers;

DROP INDEX IF EXISTS uq_clients_org_mandate_active;

ALTER TABLE clients
	DROP COLUMN mandate_id,
	ADD COLUMN source_id VARCHAR;

CREATE UNIQUE INDEX uq_clients_org_oin_cn_active
	ON clients (organization_id, oin, common_name)
	WHERE deleted_at IS NULL;
