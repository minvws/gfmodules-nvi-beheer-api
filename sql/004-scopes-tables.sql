BEGIN;
	CREATE TABLE scopes (
	    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	    name VARCHAR(50) UNIQUE,
	    created_at TIMESTAMP DEFAULT now() NOT NULL
	);
	/*Scopes as defined by the TO*/
	INSERT INTO scopes (name) VALUES 
	  ('CREATE'),
	  ('DELETE'),
	  ('READ'),
	  ('LOCALIZE');


	 -- create backup for organizations and clients 
	 -- TODO: backup indices also
	  CREATE TABLE organizations_bak AS SELECT * FROM organizations;
	  CREATE TABLE clients_bak AS SELECT * FROM clients; 
	  
	
	-- Migrate existing data into the newly created tables 
	CREATE TEMP TABLE new_clients AS SELECT DISTINCT organization_id, common_name AS name, oin, created_at, deleted_at FROM clients;
	ALTER TABLE new_clients ADD COLUMN id UUID DEFAULT gen_random_uuid();	
	
	CREATE TEMP TABLE new_org_certs AS SELECT c.organization_id, c.oin AS organization_identifier, c.common_name AS domain, c.created_at, c.deleted_at FROM  clients c; 
	ALTER TABLE new_org_certs ADD COLUMN id UUID DEFAULT gen_random_uuid();
	
	CREATE TEMP TABLE new_org_scopes AS SELECT  o.id AS organization_id, s.id AS scope_id, o.created_at FROM organizations o
 	CROSS JOIN LATERAL UNNEST(STRING_TO_ARRAY(o.scopes, ' ')) AS parsed(scope_name)
	JOIN scopes s ON s.name = UPPER(SPLIT_PART(parsed.scope_name, ':', 2))
	WHERE o.scopes IS NOT NULL AND o.scopes != '';

    CREATE TEMP TABLE new_sources AS SELECT DISTINCT ns.organization_id, ns.source_id, ns.created_at, ns.deleted_at FROM clients ns;
    ALTER TABLE new_sources ADD COLUMN id UUID DEFAULT gen_random_uuid();

	
  CREATE TEMP TABLE new_client_sources AS 
  SELECT DISTINCT
    nc.id AS client_id, 
    ns.id AS source_id 
  FROM clients cb
  JOIN new_clients nc 
   ON cb.organization_id = nc.organization_id 
   AND cb.common_name = nc.name and cb.oin = nc.oin
  JOIN new_sources ns 
    ON cb.organization_id = ns.organization_id 
   AND cb.source_id = ns.source_id
   where cb.deleted_at IS NULL AND ns.deleted_at is NULL;
  
  CREATE TEMP TABLE new_clients_scopes AS SELECT
  c.id AS client_id, 
  old_c.organization_id AS organization_id, 
  s.id AS scope_id
  FROM clients old_c
  CROSS JOIN LATERAL UNNEST(STRING_TO_ARRAY(old_c.scopes, ' ')) AS parsed(scope_name)
  JOIN scopes s ON s.name = UPPER(SPLIT_PART(parsed.scope_name, ':', 2)) 
  JOIN new_org_scopes os ON os.scope_id = s.id AND os.organization_id = old_c.organization_id 
  JOIN new_clients c on old_c.organization_id = c.organization_id and 
  old_c.oin = c.oin and old_c.common_name = c.name
  WHERE old_c.scopes IS NOT NULL AND old_c.scopes != '' and old_c.deleted_at IS NULL; 
  
  CREATE TEMP TABLE new_clients_certs AS SELECT c.id AS client_id, ca.id AS certificate_id FROM new_clients c JOIN new_org_certs ca on 
	c.organization_id = ca.organization_id AND
	c.oin = ca.organization_identifier AND
 	c.name = ca.domain AND c.deleted_at IS NULL;

	
	
	-- modify existing tables
	ALTER TABLE organizations 
	  ALTER COLUMN id SET DEFAULT gen_random_uuid(),
	  ADD COLUMN modified_at TIMESTAMP,
	  DROP COLUMN scopes;
	
	ALTER TABLE organizations 
	  RENAME register_id TO external_id;
	
	ALTER INDEX uq_organizations_register_id_active RENAME TO uq_organizations_external_id_active;
	
	ALTER TABLE clients 
	  ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ADD COLUMN name VARCHAR(100), -- nullable for now
    ADD COLUMN description VARCHAR(255),
	  ADD COLUMN modified_at TIMESTAMP,
	  DROP COLUMN common_name,
    DROP COLUMN oin,
    DROP COLUMN source_id,
	  DROP COLUMN scopes;
	
	alter table new_clients drop column oin;
	TRUNCATE TABLE clients;
	INSERT INTO clients (id, organization_id, name, created_at, deleted_at) SELECT id, organization_id, name, created_at, deleted_at FROM new_clients; 

  ALTER TABLE clients ALTER COLUMN name SET NOT NULL;
		
	-- define new tables
	
	CREATE TABLE organizations_scopes (
	  organization_id UUID NOT NULL,
	  scope_id INT NOT NULL, 
	  created_at TIMESTAMP DEFAULT now() NOT NULL,
	  
	  CONSTRAINT pk_organizations_scopes PRIMARY KEY (organization_id, scope_id),
	  CONSTRAINT fk_organization_scopes_organization FOREIGN KEY (organization_id) REFERENCES organizations (id),
	  CONSTRAINT fk_organization_scopes_scopes FOREIGN KEY (scope_id) REFERENCES scopes (id) 
	);
	
	
	CREATE TABLE clients_scopes (
	    client_id UUID NOT NULL,
	    organization_id UUID NOT NULL,
	    scope_id INT NOT NULl,
	    created_at TIMESTAMP DEFAULT now() NOT NULL,
	  
	    CONSTRAINT pk_clients_scopes PRIMARY KEY (client_id, organization_id, scope_id),
	    CONSTRAINT fk_clients_scopes_clients FOREIGN KEY (
	        client_id
	    ) REFERENCES clients (id),
	    CONSTRAINT fk_clients_scopes_scopes FOREIGN KEY (
	       organization_id, scope_id 
	    ) REFERENCES organizations_scopes (organization_id, scope_id)
	);
	    
	
	
	CREATE TABLE certificates (
	  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	  organization_identifier VARCHAR(100),
	  domain VARCHAR(100), 
	  organization_id UUID, 
	  created_at TIMESTAMP DEFAULT now() NOT NULL, 
	  modified_at TIMESTAMP, 
	  deleted_at TIMESTAMP,
	
	  CONSTRAINT fk_certificates_organizations FOREIGN KEY (organization_id) REFERENCES organizations (id)
	);
  CREATE UNIQUE INDEX  uq_organization_id_organization_identifier_domain 
    ON certificates (organization_id, organization_identifier, domain) WHERE deleted_at IS NULL;
	
	CREATE TABLE clients_certificates (
	  client_id UUID NOT NULL, 
	  certificate_id UUID NOT NULL, 
	  created_at TIMESTAMP DEFAULT now() NOT NULL, 
	
	  CONSTRAINT pk_clients_certificates PRIMARY KEY (client_id, certificate_id), 
	  CONSTRAINT fk_clients_certificates_clients FOREIGN KEY (client_id) REFERENCES clients (id),
	  CONSTRAINT fk_clients_certificates_certificates FOREIGN KEY (certificate_id) REFERENCES certificates (id)
	);
	
	
	CREATE TABLE sources (
	  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	  organization_id UUID NOT NULL, 
	  source_id VARCHAR(100) NOT NULL, 
	  name VARCHAR(150) NOT NULL,
	  created_at TIMESTAMP DEFAULT now() NOT NULL, 
	  modified_at TIMESTAMP, 
	  deleted_at TIMESTAMP,
	
	  CONSTRAINT fk_sources_organizations FOREIGN KEY (organization_id) REFERENCES organizations (id)
	);

  CREATE UNIQUE INDEX uq_sources_source_id_active 
    ON sources (organization_id, source_id)
    WHERE deleted_at IS NULL;
	
	CREATE TABLE clients_sources (
	  client_id UUID NOT NULL,
	  source_id UUID NOT NULL,  
	
	  CONSTRAINT pk_sources_clients PRIMARY KEY (source_id, client_id), 
	  CONSTRAINT fk_clients_sources_clients FOREIGN KEY (client_id) REFERENCES clients (id),
	  CONSTRAINT fk_clients_sources_sources FOREIGN KEY (source_id) REFERENCES sources (id) 
	);

  INSERT INTO sources (id,organization_id, source_id, name, created_at, deleted_at)
    SELECT id, organization_id, source_id, 'DEFAULT_NAME', created_at, deleted_at from new_sources;
	
	INSERT INTO certificates (id,organization_identifier, domain, organization_id, created_at, deleted_at) 
		SELECT id, organization_identifier, domain, organization_id, created_at, deleted_at from new_org_certs;

  INSERT INTO clients_certificates (client_id, certificate_id) SELECT client_id, certificate_id FROM new_clients_certs;  
  
  INSERT INTO clients_sources (client_id, source_id)
    SELECT client_id, source_id from new_client_sources;
	
	INSERT INTO organizations_scopes (organization_id, scope_id) SELECT organization_id, scope_id FROM new_org_scopes;

	INSERT INTO clients_scopes (client_id, organization_id, scope_id) 
		SELECT client_id, organization_id, scope_id FROM new_clients_scopes;
	
	DROP TABLE IF EXISTS new_clients;
	DROP TABLE IF EXISTS new_org_certs; 
	DROP TABLE IF EXISTS new_clients_scopes;
  DROP TABLE IF EXISTS new_sources; 
  DROP TABLE IF EXISTS new_client_sources;
	DROP TABLE IF EXISTS new_clients_certs;
COMMIT;

