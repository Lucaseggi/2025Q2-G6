-- Create database schema for structured normas

-- Main normas table
CREATE TABLE normas_structured (
    id                               SERIAL PRIMARY KEY,
    infoleg_id                       INTEGER NOT NULL UNIQUE,
    jurisdiccion                     VARCHAR(255),
    clase_norma                      VARCHAR(255),
    tipo_norma                       VARCHAR(255),
    sancion                          DATE,
    id_normas                        JSONB,
    publicacion                      DATE,
    titulo_sumario                   TEXT,
    titulo_resumido                  TEXT,
    observaciones                    TEXT,
    nro_boletin                      VARCHAR(255),
    pag_boletin                      VARCHAR(255),
    texto_resumido                   TEXT,
    texto_norma                      TEXT,
    texto_norma_actualizado          TEXT,
    estado                           VARCHAR(255),
    lista_normas_que_complementa     JSONB,
    lista_normas_que_la_complementan JSONB,

    -- Processed text fields
    purified_texto_norma             TEXT,
    purified_texto_norma_actualizado TEXT,

    -- Embedding metadata (no vectors stored here)
    embedding_model                  VARCHAR(255),
    embedding_source                 VARCHAR(255),
    embedded_at                      TIMESTAMP,
    embedding_type                   VARCHAR(255),

    -- LLM processing metadata
    llm_model_used                   VARCHAR(255),
    llm_models_used                  JSONB, -- Array of models tried
    llm_tokens_used                  INTEGER,
    llm_processing_time              FLOAT,
    llm_similarity_score             FLOAT,

    -- System timestamps
    inserted_at                      TIMESTAMP DEFAULT NOW(),
    created_at                       TIMESTAMP DEFAULT NOW(),
    updated_at                       TIMESTAMP DEFAULT NOW()
);

-- Divisions table (recursive structure)
CREATE TABLE divisions (
    id                SERIAL PRIMARY KEY,
    norma_id          INTEGER NOT NULL REFERENCES normas_structured(id) ON DELETE CASCADE,
    parent_division_id INTEGER REFERENCES divisions(id) ON DELETE CASCADE,
    name              VARCHAR(255),
    ordinal           VARCHAR(50),
    title             TEXT,
    body              TEXT,
    order_index       INTEGER,
    created_at        TIMESTAMP DEFAULT NOW()
);

-- Articles table (belongs to divisions, can be recursive)
CREATE TABLE articles (
    id                SERIAL PRIMARY KEY,
    division_id       INTEGER REFERENCES divisions(id) ON DELETE CASCADE,
    parent_article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    ordinal           VARCHAR(50),
    body              TEXT NOT NULL,
    order_index       INTEGER,
    created_at        TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_normas_infoleg ON normas_structured(infoleg_id);
CREATE INDEX idx_normas_inserted_at ON normas_structured(inserted_at);
CREATE INDEX idx_divisions_norma_id ON divisions(norma_id);
CREATE INDEX idx_divisions_parent ON divisions(parent_division_id);
CREATE INDEX idx_divisions_order ON divisions(norma_id, order_index);
CREATE INDEX idx_articles_division ON articles(division_id);
CREATE INDEX idx_articles_parent ON articles(parent_article_id);
CREATE INDEX idx_articles_order ON articles(division_id, order_index);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to normas table
CREATE TRIGGER update_normas_updated_at BEFORE UPDATE ON normas_structured
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();