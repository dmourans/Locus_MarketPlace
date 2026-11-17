"""Orquestra a construção do data warehouse do Locus: staging, DDL e DML."""
import csv
import sqlite3
import sys
from pathlib import Path

try:
    from etl.extract_transform import STAGING, gerar_staging
except ModuleNotFoundError:  # executado como script: python etl/build_dw.py
    from extract_transform import STAGING, gerar_staging

RAIZ = Path(__file__).resolve().parent.parent
SQL = RAIZ / "sql"
BANCO = SQL / "locus_dw.db"

FONTES = [
    ("stg_municipios", STAGING / "stg_municipios.csv", ","),
    ("stg_cras", STAGING / "stg_cras.csv", ","),
    ("stg_creas", STAGING / "stg_creas.csv", ","),
    ("stg_doacoes", STAGING / "stg_doacoes.csv", ","),
]

# (descrição, tabela de origem, tabela de destino)
CONFERENCIAS = [
    ("doações", "stg_doacoes", "fato_doacao"),
    ("CRAS e CREAS", "stg_cras + stg_creas", "fato_unidade_assistencial"),
]


def executar_script(conexao, nome):
    conexao.executescript((SQL / nome).read_text(encoding="utf-8"))


def carregar_staging(conexao):
    for tabela, arquivo, delimitador in FONTES:
        with open(arquivo, newline="", encoding="utf-8-sig") as f:
            leitor = csv.reader(f, delimiter=delimitador)
            next(leitor)
            linhas = list(leitor)
        colunas = len(conexao.execute(f"PRAGMA table_info({tabela})").fetchall())
        invalidas = [i for i, l in enumerate(linhas, start=2) if len(l) != colunas]
        if invalidas:
            raise ValueError(f"{arquivo.name}: linhas com colunas fora do esperado {invalidas[:5]}")
        marcadores = ", ".join("?" * colunas)
        conexao.executemany(f"INSERT INTO {tabela} VALUES ({marcadores})", linhas)
        conexao.commit()
        print(f"{tabela:<16}{len(linhas):>8} linhas")


def contar(conexao, origem):
    tabelas = [t.strip() for t in origem.split("+")]
    return sum(conexao.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tabelas)


def conferir_carga(conexao):
    print("\nConferência staging x fatos")
    divergencias = 0
    for descricao, origem, destino in CONFERENCIAS:
        total_origem = contar(conexao, origem)
        total_destino = contar(conexao, destino)
        perdidas = total_origem - total_destino
        divergencias += perdidas != 0
        print(f"{descricao:<14} origem={total_origem:>7} fato={total_destino:>7} perdidas={perdidas:>6}")
    return divergencias


def main():
    gerar_staging()
    BANCO.unlink(missing_ok=True)
    conexao = sqlite3.connect(BANCO)
    try:
        executar_script(conexao, "01_stg_ddl.sql")
        carregar_staging(conexao)
        executar_script(conexao, "03_dw_ddl.sql")
        executar_script(conexao, "04_dw_dml.sql")
        divergencias = conferir_carga(conexao)
    finally:
        conexao.close()
    print(f"\nBanco gerado em {BANCO.relative_to(RAIZ)}")
    return 1 if divergencias else 0


if __name__ == "__main__":
    sys.exit(main())
