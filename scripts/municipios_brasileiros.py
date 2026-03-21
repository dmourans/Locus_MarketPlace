import pandas as pd
from pathlib import Path
import logging

# Configuração do logging para analise de erro
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Caminho do projeto
BASE_PATH = Path("data")

RAW_PATH = BASE_PATH / "raw" / "municipios.csv"
SILVER_PATH = BASE_PATH / "processed" / "municipios_tratado.csv"

# fonte de dados
URL = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"

# Extract
def extract(url: str) -> pd.DataFrame:
    logging.info("Iniciando ingestão do dataset")

    df = pd.read_csv(url)

    logging.info(f"Dataset carregado com {len(df)} registros")

    return df

# Validate
def validate(df: pd.DataFrame) -> None:
    logging.info("Executantdo validações do dataset")

    if df.empty:
        raise ValueError("Dataset está vazio")
    
    null_counts = df.isnull().sum()

    logging.info("Valores nulos por coluna:")
    logging.info(f"\n{null_counts}")

    duplicates = df.duplicated().sum()

    logging.info(f"Registros duplicados encontrados: {duplicates}")

# Transform
def transform(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("Iniciando transformação para camada silver")

    df_clean = (
        df
        .drop_duplicates()
        .rename(columns={
            "codigo_ibge": "ibge_code",
            "nome" : "municipio"
        })
    )

    logging.info(f"Dataset após tratamento possui {len(df_clean)} registros")
    return df_clean

# Load arquivo Raw
def save_raw(df: pd.DataFrame, path: Path) -> None:
    logging.info("Salvando datase raw")

    path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(path, index=False)

    logging.info(f"Arquivo raw salvo em {path}")

# Load camada Prata
def save_silver(df: pd.DataFrame, path:Path) -> None:
    logging.info("Salvando datase silver")

    path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(path, index=False)

    logging.info(f"Arquivo silver salvo em {path}")

# Pipeline principal
def main():

    logging.info("Pipeline iniciado")

    # Extract
    df_raw = extract(URL)

    # Extract
    save_raw(df_raw, RAW_PATH)

    # Validate
    validate(df_raw)

    # Transform
    df_silver = transform(df_raw)

    # Save Silver
    save_silver(df_silver, SILVER_PATH)

    logging.info("Pipeline finalizado com sucesso")

if __name__ == "__main__":
    main()
