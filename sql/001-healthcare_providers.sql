CREATE TABLE healthcare_providers (
    id UUID PRIMARY KEY,
    ura_number VARCHAR(8) NOT NULL,
    is_source BOOLEAN NOT NULL,
    is_viewer BOOLEAN NOT NULL,
    source_id VARCHAR(250),
    oin VARCHAR,
    common_name VARCHAR,
    status VARCHAR(20),
    deleted_at TIMESTAMP
);
