CREATE TABLE healthcare_providers (
    id UUID PRIMARY KEY,
    ura_number VARCHAR(8) NOT NULL,
    is_source BOOLEAN NOT NULL,
    is_viewer BOOLEAN NOT NULL,
    source_id VARCHAR(250),
    oin_certificate VARCHAR,
    deleted_at TIMESTAMP,
    status VARCHAR(20),

    CONSTRAINT ura_number_source_idx UNIQUE (ura_number, source_id),
    CONSTRAINT ura_number_oin_certificate_idx UNIQUE (
        ura_number, oin_certificate
    )

);
