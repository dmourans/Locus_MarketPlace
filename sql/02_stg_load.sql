.import --csv --skip 1 data/processed/municipios_tratado.csv stg_municipios
.import --csv --skip 1 data/raw/CRAS_BRASIL.csv stg_cras
.import --csv --skip 1 data/raw/CREAS_BRASIL.csv stg_creas
.separator ';'
.import --skip 1 data/raw/Donatarios2025.csv stg_doacoes
