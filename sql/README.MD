# Data Warehouse — Locus MarketPlace

Data warehouse em SQLite 3: **6 dimensões** e **2 fatos**, com chaves e restrições.  
Carga a partir do **staging**, em **transação** (`BEGIN` / `COMMIT`).

## Arquivos

| Arquivo | Função |
|---|---|
| `01_stg_ddl.sql` | DDL das tabelas de staging |
| `02_stg_load.sql` | Import dos CSVs para o staging |
| `03_dw_ddl.sql` | DDL do DW (dimensões, fatos, PK, FK, UNIQUE, CHECK) |
| `04_dw_dml.sql` | DML: carga das dimensões e dos fatos a partir do staging |
| `05_olap_operacoes.sql` | 10 consultas OLAP sobre o DW |

O SQLite não tem `CREATE SCHEMA`. As tabelas usam prefixos `stg_`, `dim_` e `fato_`.

## Como recriar o banco

### Opção 1 — ETL em Python (recomendada)

Na raiz do projeto:

```bash
python etl/build_dw.py
```

O script aplica as regras de limpeza, carrega o staging, executa o DDL e o DML e confere a carga.

### Opção 2 — manualmente pelo `sqlite3`

Na raiz do projeto:

```bash
sqlite3 sql/locus_dw.db
```

No prompt `sqlite>`, um comando por vez:

```
.read sql/01_stg_ddl.sql
.read sql/02_stg_load.sql
.read sql/03_dw_ddl.sql
.read sql/04_dw_dml.sql
```

Essa opção importa os CSVs sem as regras de limpeza do ETL.

## Modelo

- **Dimensões:** `dim_data`, `dim_uf`, `dim_municipio`, `dim_item`, `dim_doador`, `dim_unidade`
- **Fatos:** `fato_doacao` (quantidade doada), `fato_unidade_assistencial` (CRAS/CREAS)

Documentação completa em [`docs/modelo_dimensional.md`](../docs/modelo_dimensional.md).

## Fontes

`data/processed/municipios_tratado.csv`, `data/raw/CRAS_BRASIL.csv`, `data/raw/CREAS_BRASIL.csv`, `data/raw/Donatarios2025.csv`
