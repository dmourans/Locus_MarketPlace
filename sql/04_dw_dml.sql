PRAGMA foreign_keys = ON;

BEGIN;

-- Reexecutar o script não duplica: apaga fatos e depois dimensões
DELETE FROM fato_doacao;
DELETE FROM fato_unidade_assistencial;
DELETE FROM dim_unidade;
DELETE FROM dim_doador;
DELETE FROM dim_item;
DELETE FROM dim_municipio;
DELETE FROM dim_uf;
DELETE FROM dim_data;

-- ------------------------------------------------------------
-- dim_uf
-- ------------------------------------------------------------
INSERT INTO dim_uf (codigo_uf, sigla, nome) VALUES
    ('11', 'RO', 'Rondônia'),
    ('12', 'AC', 'Acre'),
    ('13', 'AM', 'Amazonas'),
    ('14', 'RR', 'Roraima'),
    ('15', 'PA', 'Pará'),
    ('16', 'AP', 'Amapá'),
    ('17', 'TO', 'Tocantins'),
    ('21', 'MA', 'Maranhão'),
    ('22', 'PI', 'Piauí'),
    ('23', 'CE', 'Ceará'),
    ('24', 'RN', 'Rio Grande do Norte'),
    ('25', 'PB', 'Paraíba'),
    ('26', 'PE', 'Pernambuco'),
    ('27', 'AL', 'Alagoas'),
    ('28', 'SE', 'Sergipe'),
    ('29', 'BA', 'Bahia'),
    ('31', 'MG', 'Minas Gerais'),
    ('32', 'ES', 'Espírito Santo'),
    ('33', 'RJ', 'Rio de Janeiro'),
    ('35', 'SP', 'São Paulo'),
    ('41', 'PR', 'Paraná'),
    ('42', 'SC', 'Santa Catarina'),
    ('43', 'RS', 'Rio Grande do Sul'),
    ('50', 'MS', 'Mato Grosso do Sul'),
    ('51', 'MT', 'Mato Grosso'),
    ('52', 'GO', 'Goiás'),
    ('53', 'DF', 'Distrito Federal');

-- ------------------------------------------------------------
-- dim_data (doações DD/MM/AAAA + atualização CRAS/CREAS ISO)
-- ------------------------------------------------------------
INSERT INTO dim_data (data, dia, mes, ano, trimestre, dia_semana, nome_mes)
SELECT
    x.data,
    CAST(substr(x.data, 9, 2) AS INTEGER),
    CAST(substr(x.data, 6, 2) AS INTEGER),
    CAST(substr(x.data, 1, 4) AS INTEGER),
    CASE
        WHEN CAST(substr(x.data, 6, 2) AS INTEGER) BETWEEN 1 AND 3 THEN 1
        WHEN CAST(substr(x.data, 6, 2) AS INTEGER) BETWEEN 4 AND 6 THEN 2
        WHEN CAST(substr(x.data, 6, 2) AS INTEGER) BETWEEN 7 AND 9 THEN 3
        ELSE 4
    END,
    CASE strftime('%w', x.data)
        WHEN '0' THEN 'domingo'
        WHEN '1' THEN 'segunda-feira'
        WHEN '2' THEN 'terça-feira'
        WHEN '3' THEN 'quarta-feira'
        WHEN '4' THEN 'quinta-feira'
        WHEN '5' THEN 'sexta-feira'
        ELSE 'sábado'
    END,
    CASE CAST(substr(x.data, 6, 2) AS INTEGER)
        WHEN 1 THEN 'janeiro'
        WHEN 2 THEN 'fevereiro'
        WHEN 3 THEN 'março'
        WHEN 4 THEN 'abril'
        WHEN 5 THEN 'maio'
        WHEN 6 THEN 'junho'
        WHEN 7 THEN 'julho'
        WHEN 8 THEN 'agosto'
        WHEN 9 THEN 'setembro'
        WHEN 10 THEN 'outubro'
        WHEN 11 THEN 'novembro'
        ELSE 'dezembro'
    END
FROM (
    SELECT DISTINCT
        substr(data_inversa, 7, 4) || '-' ||
        substr(data_inversa, 4, 2) || '-' ||
        substr(data_inversa, 1, 2) AS data
    FROM stg_doacoes
    WHERE data_inversa IS NOT NULL
      AND length(trim(data_inversa)) = 10
    UNION
    SELECT DISTINCT substr(data_atualizacao, 1, 10)
    FROM stg_cras
    WHERE data_atualizacao IS NOT NULL
      AND length(data_atualizacao) >= 10
    UNION
    SELECT DISTINCT substr(data_atualizacao, 1, 10)
    FROM stg_creas
    WHERE data_atualizacao IS NOT NULL
      AND length(data_atualizacao) >= 10
) x
WHERE x.data GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]';

-- ------------------------------------------------------------
-- dim_municipio
-- ------------------------------------------------------------
INSERT INTO dim_municipio (
    ibge_code, municipio, capital, codigo_uf, ddd, latitude, longitude, fuso_horario
)
SELECT
    ibge_code,
    municipio,
    CAST(capital AS INTEGER),
    codigo_uf,
    ddd,
    CAST(latitude AS REAL),
    CAST(longitude AS REAL),
    fuso_horario
FROM stg_municipios
WHERE ibge_code IS NOT NULL AND trim(ibge_code) <> '';

-- nome de município sem acento, para casar com stg_doacoes
DROP TABLE IF EXISTS tmp_mun_norm;
CREATE TEMP TABLE tmp_mun_norm AS
SELECT
    sk_municipio,
    codigo_uf,
    UPPER(REPLACE(REPLACE(REPLACE(REPLACE(
    REPLACE(REPLACE(REPLACE(REPLACE(
    REPLACE(REPLACE(REPLACE(REPLACE(
    REPLACE(REPLACE(REPLACE(REPLACE(
    REPLACE(REPLACE(REPLACE(REPLACE(
    REPLACE(REPLACE(REPLACE(REPLACE(
    municipio,
    'á','a'),'à','a'),'â','a'),'ã','a'),
    'é','e'),'ê','e'),
    'í','i'),
    'ó','o'),'ô','o'),'õ','o'),
    'ú','u'),
    'ç','c'),
    'Á','A'),'À','A'),'Â','A'),'Ã','A'),
    'É','E'),'Ê','E'),
    'Í','I'),
    'Ó','O'),'Ô','O'),'Õ','O'),
    'Ú','U'),
    'Ç','C')) AS municipio_norm
FROM dim_municipio;

-- ------------------------------------------------------------
-- dim_item
-- ------------------------------------------------------------
INSERT INTO dim_item (item, grupo_item)
SELECT DISTINCT item, grupo_item
FROM stg_doacoes
WHERE item IS NOT NULL AND trim(item) <> ''
  AND grupo_item IS NOT NULL AND trim(grupo_item) <> '';

-- ------------------------------------------------------------
-- dim_doador
-- ------------------------------------------------------------
INSERT INTO dim_doador (idade, sexo, primeira_doacao)
SELECT DISTINCT
    CAST(idade AS INTEGER),
    sexo,
    primeira_doacao
FROM stg_doacoes
WHERE idade GLOB '[0-9]*'
  AND sexo IS NOT NULL AND trim(sexo) <> ''
  AND primeira_doacao IN ('Sim', 'Não');

-- ------------------------------------------------------------
-- dim_unidade: ONG (doações) + CRAS + CREAS
-- ------------------------------------------------------------
INSERT INTO dim_unidade (id_origem, tipo, nome, uf, cidade)
SELECT
    id_ong,
    tipo_ong,
    NULL,
    MIN(uf),
    MIN(municipio)
FROM stg_doacoes
WHERE id_ong IS NOT NULL AND trim(id_ong) <> ''
  AND tipo_ong IN ('ONG', 'CRAS', 'CREAS')
GROUP BY id_ong, tipo_ong;

INSERT INTO dim_unidade (
    id_origem, tipo, nome, uf, cidade, endereco, bairro, cep, telefone
)
SELECT
    id_equipamento,
    'CRAS',
    nome,
    uf,
    cidade,
    endereco,
    bairro,
    cep,
    telefone
FROM stg_cras
WHERE id_equipamento IS NOT NULL AND trim(id_equipamento) <> '';

INSERT INTO dim_unidade (
    id_origem, tipo, nome, uf, cidade, endereco, bairro, cep, telefone
)
SELECT
    id_equipamento,
    'CREAS',
    nome,
    uf,
    cidade,
    endereco,
    bairro,
    cep,
    telefone
FROM stg_creas
WHERE id_equipamento IS NOT NULL AND trim(id_equipamento) <> '';

-- ------------------------------------------------------------
-- fato_doacao
-- ------------------------------------------------------------
INSERT INTO fato_doacao (
    sk_data, sk_uf, sk_municipio, sk_item, sk_doador, sk_unidade,
    id_origem, horario, qtd
)
SELECT
    d.sk_data,
    uf.sk_uf,
    n.sk_municipio,
    i.sk_item,
    doa.sk_doador,
    un.sk_unidade,
    s.id,
    s.horario,
    CAST(s.qtd AS INTEGER)
FROM stg_doacoes s
JOIN dim_data d
  ON d.data = substr(s.data_inversa, 7, 4) || '-' ||
              substr(s.data_inversa, 4, 2) || '-' ||
              substr(s.data_inversa, 1, 2)
JOIN dim_uf uf
  ON uf.sigla = s.uf
JOIN dim_item i
  ON i.item = s.item AND i.grupo_item = s.grupo_item
JOIN dim_doador doa
  ON doa.idade = CAST(s.idade AS INTEGER)
 AND doa.sexo = s.sexo
 AND doa.primeira_doacao = s.primeira_doacao
LEFT JOIN dim_unidade un
  ON un.tipo = s.tipo_ong AND un.id_origem = s.id_ong
LEFT JOIN tmp_mun_norm n
  ON n.codigo_uf = uf.codigo_uf
 AND n.municipio_norm = s.municipio;

-- ------------------------------------------------------------
-- fato_unidade_assistencial (1 linha por CRAS/CREAS)
-- ------------------------------------------------------------
INSERT INTO fato_unidade_assistencial (
    sk_unidade, sk_municipio, sk_uf, sk_data, qtd_unidades
)
SELECT
    un.sk_unidade,
    m.sk_municipio,
    uf.sk_uf,
    d.sk_data,
    1
FROM stg_cras s
JOIN dim_unidade un
  ON un.tipo = 'CRAS' AND un.id_origem = s.id_equipamento
LEFT JOIN dim_uf uf
  ON uf.sigla = s.uf
LEFT JOIN dim_municipio m
  ON m.ibge_code = s.ibge
  OR (length(s.ibge) = 6 AND substr(m.ibge_code, 1, 6) = s.ibge)
LEFT JOIN dim_data d
  ON d.data = substr(s.data_atualizacao, 1, 10);

INSERT INTO fato_unidade_assistencial (
    sk_unidade, sk_municipio, sk_uf, sk_data, qtd_unidades
)
SELECT
    un.sk_unidade,
    m.sk_municipio,
    uf.sk_uf,
    d.sk_data,
    1
FROM stg_creas s
JOIN dim_unidade un
  ON un.tipo = 'CREAS' AND un.id_origem = s.id_equipamento
LEFT JOIN dim_uf uf
  ON uf.sigla = s.uf
LEFT JOIN dim_municipio m
  ON m.ibge_code = s.ibge
  OR (length(s.ibge) = 6 AND substr(m.ibge_code, 1, 6) = s.ibge)
LEFT JOIN dim_data d
  ON d.data = substr(s.data_atualizacao, 1, 10);

COMMIT;

SELECT 'dim_data' AS tabela, COUNT(*) AS linhas FROM dim_data
UNION ALL SELECT 'dim_uf', COUNT(*) FROM dim_uf
UNION ALL SELECT 'dim_municipio', COUNT(*) FROM dim_municipio
UNION ALL SELECT 'dim_item', COUNT(*) FROM dim_item
UNION ALL SELECT 'dim_doador', COUNT(*) FROM dim_doador
UNION ALL SELECT 'dim_unidade', COUNT(*) FROM dim_unidade
UNION ALL SELECT 'fato_doacao', COUNT(*) FROM fato_doacao
UNION ALL SELECT 'fato_unidade_assistencial', COUNT(*) FROM fato_unidade_assistencial;
