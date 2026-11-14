CREATE TABLE stg_municipios (
    ibge_code     TEXT,
    municipio     TEXT,
    latitude      TEXT,
    longitude     TEXT,
    capital       TEXT,
    codigo_uf     TEXT,
    siafi_id      TEXT,
    ddd           TEXT,
    fuso_horario  TEXT
);

CREATE TABLE stg_cras (
    id_equipamento   TEXT,
    ibge             TEXT,
    uf               TEXT,
    cidade           TEXT,
    nome             TEXT,
    responsavel      TEXT,
    telefone         TEXT,
    endereco         TEXT,
    numero           TEXT,
    complemento      TEXT,
    referencia       TEXT,
    bairro           TEXT,
    cep              TEXT,
    georef_location  TEXT,
    data_atualizacao TEXT
);

CREATE TABLE stg_creas (
    id_equipamento   TEXT,
    ibge             TEXT,
    uf               TEXT,
    cidade           TEXT,
    nome             TEXT,
    responsavel      TEXT,
    telefone         TEXT,
    endereco         TEXT,
    numero           TEXT,
    complemento      TEXT,
    referencia       TEXT,
    bairro           TEXT,
    cep              TEXT,
    georef_location  TEXT,
    data_atualizacao TEXT
);

CREATE TABLE stg_doacoes (
    id               TEXT,
    data_inversa     TEXT,
    dia_semana       TEXT,
    horario          TEXT,
    uf               TEXT,
    municipio        TEXT,
    item             TEXT,
    grupo_item       TEXT,
    primeira_doacao  TEXT,
    idade            TEXT,
    sexo             TEXT,
    qtd              TEXT,
    tipo_ong         TEXT,
    id_ong           TEXT
);
