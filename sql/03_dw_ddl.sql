PRAGMA foreign_keys = ON;

-- ============================================================
-- DIMENSÕES (6)
-- ============================================================

CREATE TABLE dim_data (
    sk_data     INTEGER PRIMARY KEY AUTOINCREMENT,
    data        TEXT    NOT NULL UNIQUE, -- AAAA-MM-DD
    dia         INTEGER NOT NULL CHECK (dia BETWEEN 1 AND 31),
    mes         INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    ano         INTEGER NOT NULL,
    trimestre   INTEGER NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    dia_semana  TEXT    NOT NULL,
    nome_mes    TEXT    NOT NULL
);

CREATE TABLE dim_uf (
    sk_uf      INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_uf  TEXT    NOT NULL UNIQUE,
    sigla      TEXT    NOT NULL UNIQUE,
    nome       TEXT    NOT NULL
);

CREATE TABLE dim_municipio (
    sk_municipio INTEGER PRIMARY KEY AUTOINCREMENT,
    ibge_code    TEXT    NOT NULL UNIQUE,
    municipio    TEXT    NOT NULL,
    capital      INTEGER NOT NULL CHECK (capital IN (0, 1)),
    codigo_uf    TEXT    NOT NULL,
    ddd          TEXT,
    latitude     REAL,
    longitude    REAL,
    fuso_horario TEXT
);

CREATE TABLE dim_item (
    sk_item     INTEGER PRIMARY KEY AUTOINCREMENT,
    item        TEXT NOT NULL,
    grupo_item  TEXT NOT NULL,
    UNIQUE (item, grupo_item)
);

CREATE TABLE dim_doador (
    sk_doador         INTEGER PRIMARY KEY AUTOINCREMENT,
    idade             INTEGER NOT NULL CHECK (idade >= 0),
    sexo              TEXT    NOT NULL,
    primeira_doacao   TEXT    NOT NULL CHECK (primeira_doacao IN ('Sim', 'Não')),
    UNIQUE (idade, sexo, primeira_doacao)
);

CREATE TABLE dim_unidade (
    sk_unidade  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_origem   TEXT NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('ONG', 'CRAS', 'CREAS')),
    nome        TEXT,
    uf          TEXT,
    cidade      TEXT,
    endereco    TEXT,
    bairro      TEXT,
    cep         TEXT,
    telefone    TEXT,
    UNIQUE (tipo, id_origem)
);

-- ============================================================
-- FATOS (2)
-- ============================================================

CREATE TABLE fato_doacao (
    sk_doacao    INTEGER PRIMARY KEY AUTOINCREMENT,
    sk_data      INTEGER NOT NULL,
    sk_uf        INTEGER NOT NULL,
    sk_municipio INTEGER,
    sk_item      INTEGER NOT NULL,
    sk_doador    INTEGER NOT NULL,
    sk_unidade   INTEGER,
    id_origem    TEXT,
    horario      TEXT,
    qtd          INTEGER NOT NULL CHECK (qtd >= 0),
    FOREIGN KEY (sk_data)      REFERENCES dim_data (sk_data),
    FOREIGN KEY (sk_uf)        REFERENCES dim_uf (sk_uf),
    FOREIGN KEY (sk_municipio) REFERENCES dim_municipio (sk_municipio),
    FOREIGN KEY (sk_item)      REFERENCES dim_item (sk_item),
    FOREIGN KEY (sk_doador)    REFERENCES dim_doador (sk_doador),
    FOREIGN KEY (sk_unidade)   REFERENCES dim_unidade (sk_unidade)
);

CREATE TABLE fato_unidade_assistencial (
    sk_fato_unidade INTEGER PRIMARY KEY AUTOINCREMENT,
    sk_unidade      INTEGER NOT NULL,
    sk_municipio    INTEGER,
    sk_uf           INTEGER,
    sk_data         INTEGER,
    qtd_unidades    INTEGER NOT NULL DEFAULT 1 CHECK (qtd_unidades >= 0),
    FOREIGN KEY (sk_unidade)   REFERENCES dim_unidade (sk_unidade),
    FOREIGN KEY (sk_municipio) REFERENCES dim_municipio (sk_municipio),
    FOREIGN KEY (sk_uf)        REFERENCES dim_uf (sk_uf),
    FOREIGN KEY (sk_data)      REFERENCES dim_data (sk_data)
);
