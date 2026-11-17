-- Operações OLAP sobre o data warehouse do Locus (SQLite).
-- Medida principal: SUM(fato_doacao.qtd). Execute no banco gerado por etl/build_dw.py.

-- 1. Roll-up: mês -> trimestre -> ano
SELECT ano, trimestre, mes, total
FROM (
    SELECT d.ano, d.trimestre, d.mes AS ordem, d.nome_mes AS mes, SUM(f.qtd) AS total
    FROM fato_doacao f
    JOIN dim_data d ON d.sk_data = f.sk_data
    GROUP BY d.ano, d.trimestre, d.mes, d.nome_mes
    UNION ALL
    SELECT d.ano, d.trimestre, 13, 'subtotal trimestre', SUM(f.qtd)
    FROM fato_doacao f
    JOIN dim_data d ON d.sk_data = f.sk_data
    GROUP BY d.ano, d.trimestre
    UNION ALL
    SELECT d.ano, 5, 14, 'total ano', SUM(f.qtd)
    FROM fato_doacao f
    JOIN dim_data d ON d.sk_data = f.sk_data
    GROUP BY d.ano
)
ORDER BY ano, trimestre, ordem;

-- 2. Drill-down: grupo de item -> item
SELECT i.grupo_item, i.item, SUM(f.qtd) AS total,
       ROUND(100.0 * SUM(f.qtd) / SUM(SUM(f.qtd)) OVER (PARTITION BY i.grupo_item), 1) AS pct_no_grupo
FROM fato_doacao f
JOIN dim_item i ON i.sk_item = f.sk_item
GROUP BY i.grupo_item, i.item
ORDER BY i.grupo_item, total DESC;

-- 3. Slice: grupo de item fixo em 'Alimentação', evolução mensal
SELECT d.mes, d.nome_mes, SUM(f.qtd) AS total
FROM fato_doacao f
JOIN dim_data d ON d.sk_data = f.sk_data
JOIN dim_item i ON i.sk_item = f.sk_item
WHERE i.grupo_item = 'Alimentação'
GROUP BY d.mes, d.nome_mes
ORDER BY d.mes;

-- 4. Dice: 1º semestre, dois grupos de item, doadoras do sexo feminino
SELECT i.grupo_item, d.trimestre, SUM(f.qtd) AS total, COUNT(*) AS doacoes
FROM fato_doacao f
JOIN dim_data d ON d.sk_data = f.sk_data
JOIN dim_item i ON i.sk_item = f.sk_item
JOIN dim_doador p ON p.sk_doador = f.sk_doador
WHERE d.trimestre IN (1, 2)
  AND i.grupo_item IN ('Alimentação', 'Higiene')
  AND p.sexo = 'Feminino'
GROUP BY i.grupo_item, d.trimestre
ORDER BY i.grupo_item, d.trimestre;

-- 5. Pivot: grupo de item nas linhas, trimestres nas colunas
SELECT i.grupo_item,
       SUM(CASE WHEN d.trimestre = 1 THEN f.qtd ELSE 0 END) AS tri_1,
       SUM(CASE WHEN d.trimestre = 2 THEN f.qtd ELSE 0 END) AS tri_2,
       SUM(CASE WHEN d.trimestre = 3 THEN f.qtd ELSE 0 END) AS tri_3,
       SUM(CASE WHEN d.trimestre = 4 THEN f.qtd ELSE 0 END) AS tri_4,
       SUM(f.qtd) AS total
FROM fato_doacao f
JOIN dim_data d ON d.sk_data = f.sk_data
JOIN dim_item i ON i.sk_item = f.sk_item
GROUP BY i.grupo_item
ORDER BY total DESC;

-- 6. Cube: todas as combinações de grupo de item e trimestre
WITH base AS (
    SELECT i.grupo_item, d.trimestre, SUM(f.qtd) AS total
    FROM fato_doacao f
    JOIN dim_data d ON d.sk_data = f.sk_data
    JOIN dim_item i ON i.sk_item = f.sk_item
    GROUP BY i.grupo_item, d.trimestre
)
SELECT grupo_item, CAST(trimestre AS TEXT) AS trimestre, total FROM base
UNION ALL
SELECT grupo_item, 'todos', SUM(total) FROM base GROUP BY grupo_item
UNION ALL
SELECT 'todos', CAST(trimestre AS TEXT), SUM(total) FROM base GROUP BY trimestre
UNION ALL
SELECT 'todos', 'todos', SUM(total) FROM base
ORDER BY grupo_item, trimestre;

-- 7. Drill-across: doações (fato_doacao) x rede CRAS/CREAS (fato_unidade_assistencial) por município
WITH doacoes AS (
    SELECT sk_municipio, SUM(qtd) AS itens_doados
    FROM fato_doacao
    GROUP BY sk_municipio
),
rede AS (
    SELECT sk_municipio, SUM(qtd_unidades) AS unidades
    FROM fato_unidade_assistencial
    GROUP BY sk_municipio
)
SELECT m.municipio, d.itens_doados, r.unidades,
       ROUND(1.0 * d.itens_doados / r.unidades, 1) AS itens_por_unidade
FROM doacoes d
JOIN rede r ON r.sk_municipio = d.sk_municipio
JOIN dim_municipio m ON m.sk_municipio = d.sk_municipio
ORDER BY d.itens_doados DESC
LIMIT 15;

-- 8. Ranking: 10 municípios que mais receberam doações
SELECT RANK() OVER (ORDER BY SUM(f.qtd) DESC) AS posicao,
       m.municipio, SUM(f.qtd) AS total
FROM fato_doacao f
JOIN dim_municipio m ON m.sk_municipio = f.sk_municipio
GROUP BY m.sk_municipio, m.municipio
ORDER BY posicao
LIMIT 10;

-- 9. Participação e acumulado por grupo de item
SELECT grupo_item, total,
       ROUND(100.0 * total / SUM(total) OVER (), 1) AS pct,
       ROUND(100.0 * SUM(total) OVER (ORDER BY total DESC) / SUM(total) OVER (), 1) AS pct_acumulado
FROM (
    SELECT i.grupo_item, SUM(f.qtd) AS total
    FROM fato_doacao f
    JOIN dim_item i ON i.sk_item = f.sk_item
    GROUP BY i.grupo_item
)
ORDER BY total DESC;

-- 10. Perfil do doador: faixa etária e primeira doação
SELECT CASE
           WHEN p.idade < 18 THEN '0-17'
           WHEN p.idade < 30 THEN '18-29'
           WHEN p.idade < 45 THEN '30-44'
           WHEN p.idade < 60 THEN '45-59'
           ELSE '60+'
       END AS faixa_etaria,
       p.primeira_doacao,
       COUNT(*) AS doacoes,
       SUM(f.qtd) AS itens,
       ROUND(AVG(f.qtd), 1) AS media_por_doacao
FROM fato_doacao f
JOIN dim_doador p ON p.sk_doador = f.sk_doador
GROUP BY faixa_etaria, p.primeira_doacao
ORDER BY faixa_etaria, p.primeira_doacao;
