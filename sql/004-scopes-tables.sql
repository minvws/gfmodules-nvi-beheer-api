CREATE TABLE scopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE,
    created_at TIMESTAMP DEFAULT now() NOT NULL,
    modified_at TIMESTAMP NULL, 
    deleted_at TIMESTAMP NULL
);
/*Scopes as defined by the TO*/
INSERT INTO scopes (name) values 
  ('nvi:create'),
  ('nvi:delete'),
  ('nvi:read'),
  ('nvi:localize');

CREATE TABLE organizations_scopes (
  organization_id UUID NOT NULL,
  scope_id UUID NOT NULL, 
  
  CONSTRAINT pk_organizations_scopes PRIMARY KEY (organization_id, scope_id),
  CONSTRAINT fk_organization_scopes_organization FOREIGN KEY (organization_id) REFERENCES organizations (id),
  CONSTRAINT fk_organization_scopes_scopes FOREIGN KEY (scope_id) REFERENCES scopes (id) 
);

CREATE TABLE clients_scopes (
    client_id UUID NOT NULL,
    scope_id UUID NOT NULL,
  
    CONSTRAINT pk_clients_scopes PRIMARY KEY (client_id, scope_id),
    CONSTRAINT fk_clients_scopes_clients FOREIGN KEY (
        client_id
    ) REFERENCES clients (id),
    CONSTRAINT fk_clients_scopes_scopes FOREIGN KEY (
        scope_id
    ) REFERENCES scopes (id)
);

-- Migrate existing data into the newly created tables 
WITH org_scopes AS (
    SELECT 
        o.id AS organization_id, 
        s.id AS scope_id
    FROM organizations o

    CROSS JOIN LATERAL UNNEST(STRING_TO_ARRAY(o.scopes, ' ')) AS parsed(scope_name)
    JOIN scopes s ON s.name = parsed.scope_name
    WHERE o.scopes IS NOT NULL AND o.scopes != ''
)

INSERT INTO organizations_scopes (organization_id, scope_id) SELECT organization_id, scope_id FROM org_scopes;

WITH c_scopes AS (
    SELECT 
        c.id AS client_id, 
        s.id AS scope_id
    FROM clients c

    CROSS JOIN LATERAL UNNEST(STRING_TO_ARRAY(c.scopes, ' ')) AS parsed(scope_name)
    JOIN scopes s ON s.name = parsed.scope_name
    WHERE c.scopes IS NOT NULL AND c.scopes != ''
)

insert into clients_scopes (client_id, scope_id) select client_id, scope_id from c_scopes;

ALTER TABLE organizations DROP COLUMN scopes;
ALTER TABLE clients DROP COLUMN scopes;
