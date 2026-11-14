# Data Warehouse — Locus MarketPlace

Esquema `dw` em SQLite3: **6 dimensões** e **2 fatos**, com chaves e restrições.  
Carga a partir do **staging**, em **transação** (`BEGIN` / `COMMIT`).

## Arquivos

| Arquivo | Função |
|---|---|
| `01_stg_ddl.sql` | DDL das tabelas de staging |
| `02_stg_load.sql` | Import dos CSVs para o staging |
| `03_dw_ddl.sql` | DDL do DW (dimensões, fatos, PK, FK, UNIQUE, CHECK) |
| `04_dw_dml.sql` | DML: carga das dimensões e dos fatos a partir do staging |

O SQLite não tem `CREATE SCHEMA`. As tabelas usam prefixos `stg_`, `dim_` e `fato_`.

## Como recriar o banco

No terminal, na raiz do projeto:

```bash
sqlite3 sql/locus_dw.db


No prompt sqlite>, um comando por vez:

.read sql/01_stg_ddl.sql
.read sql/02_stg_load.sql
.read sql/03_dw_ddl.sql
.read sql/04_dw_dml.sql

Modelo
Dimensões: dim_data, dim_uf, dim_municipio, dim_item, dim_doador, dim_unidade
Fatos: fato_doacao (quantidade doada), fato_unidade_assistencial (CRAS/CREAS)

Fontes: data/processed/municipios_tratado.csv, data/raw/CRAS_BRASIL.csv, data/raw/CREAS_BRASIL.csv, data/raw/Donatarios2025.csv