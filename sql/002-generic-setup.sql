
CREATE TABLE organizations (
	id uuid PRIMARY KEY,
	name varchar NOT NULL,
	register_id varchar NOT NULL,
	scopes varchar NULL,
	deleted_at timestamp NULL,
	created_at timestamp DEFAULT now() NOT NULL
);

CREATE UNIQUE INDEX uq_organizations_register_id_active
    ON organizations (register_id)
    WHERE deleted_at IS NULL;

CREATE TABLE clients (
	id uuid PRIMARY KEY,
	organization_id UUID NOT NULL REFERENCES organizations(id),
	oin varchar NOT NULL,
	common_name varchar NOT NULL,
	scopes varchar NULL,
	mandate_id varchar NOT NULL,
	created_at timestamp DEFAULT now() NOT NULL,
	deleted_at timestamp NULL
);

CREATE UNIQUE INDEX uq_clients_org_mandate_active
    ON clients (organization_id, mandate_id)
    WHERE deleted_at IS NULL;