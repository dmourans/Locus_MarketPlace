"""Extração e transformação: dos CSVs de origem para a área de staging.

Lê as quatro fontes do data warehouse, aplica as regras de limpeza T1 a T8 e
grava um CSV por tabela em data/staging/, no layout de sql/01_stg_ddl.sql.
As regras tratam apenas valores: nenhuma coluna é criada, removida ou
reordenada.

    T1  layout       cabeçalho no padrão do staging, campos lidos como texto
    T2  espaços      pontas, repetições, quebras de linha e invisíveis
    T3  ausentes     "-", "s/n" e "0" viram vazio nos campos opcionais
    T4  categorias   UF, sexo, primeira doação e tipo nos valores do DW
    T5  datas        data e horário validados; dia da semana recalculado
    T6  números      idade, quantidade e códigos nas restrições do DW
    T7  localização  UF e cidade pelo código IBGE; CEP com 8 dígitos
    T8  duplicados   linhas idênticas e chaves de negócio repetidas

O DML descarta em silêncio as linhas que não casam com as dimensões (data
inválida, idade não numérica, UF desconhecida). Aqui elas vão para
data/staging/rejeitados.csv com o motivo, e a conta fecha:
lidas = gravadas + duplicadas + rejeitadas.
"""
import csv
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime
from functools import partial
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
STAGING = RAIZ / "data" / "staging"
DDL_STAGING = RAIZ / "sql" / "01_stg_ddl.sql"

# tabela de staging: (arquivo de origem, separador, chave de negócio)
FONTES = {
    "stg_municipios": (
        RAIZ / "data/processed/municipios_tratado.csv", ",", "ibge_code"),
    "stg_cras": (RAIZ / "data/raw/CRAS_BRASIL.csv", ",", "id_equipamento"),
    "stg_creas": (RAIZ / "data/raw/CREAS_BRASIL.csv", ",", "id_equipamento"),
    "stg_doacoes": (RAIZ / "data/raw/Donatarios2025.csv", ";", None),
}

DESCRICAO = {
    "T1": "layout do staging",
    "T2": "espaços e caracteres invisíveis",
    "T3": "marcadores de ausência",
    "T4": "categorias padronizadas",
    "T5": "datas, horários e dia da semana",
    "T6": "números e códigos",
    "T7": "localização (IBGE, CEP, coordenadas)",
    "T8": "duplicados e chaves de negócio",
}
AVISO_ID_ONG = "id_ong em notação científica (precisão perdida na origem)"

UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}
SIGLAS = set(UF_POR_CODIGO.values())
DIAS_SEMANA = (
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
)
SEXOS = {
    "masculino": "Masculino", "m": "Masculino",
    "feminino": "Feminino", "f": "Feminino",
}
SIM_NAO = {"sim": "Sim", "s": "Sim", "nao": "Não", "n": "Não"}
OPCIONAIS = ("responsavel", "telefone", "numero", "complemento", "referencia")

INVISIVEIS = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏﻿]")
ESPACOS = re.compile(r"\s+")
MARCADOR_AUSENTE = re.compile(
    r"s/?no?|sem numero|nao( tem| possui| ha| informado)?"
    r"|nenhum|n/[aid]|x+|null|nan|none")
HORARIO = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?")
LINHA_RESUMO = "{:<16}{:>8}{:>10}{:>12}{:>12}"


class Qualidade:
    """O que as regras alteraram, rejeitaram ou sinalizaram em cada tabela."""

    def __init__(self):
        # tabela: (lidas, gravadas, duplicadas, rejeitadas)
        self.linhas = {}
        # (tabela, regra): linhas alteradas
        self.alteradas = Counter()
        # (tabela, linhas, descrição)
        self.avisos = []
        # [tabela, registro, regra, motivo, conteúdo original]
        self.rejeitados = []

    def imprimir(self):
        cabecalho = ("tabela", "lidas", "gravadas", "duplicadas", "rejeitadas")
        print("Extração e transformação (regras T1 a T8)")
        print(LINHA_RESUMO.format(*cabecalho))
        for tabela, contagens in self.linhas.items():
            print(LINHA_RESUMO.format(tabela, *contagens))
        print("\nLinhas alteradas por regra")
        for (tabela, regra), total in sorted(self.alteradas.items()):
            print(f"{tabela:<16}{regra}  {DESCRICAO[regra]:<38}{total:>8}")
        for tabela, total, descricao in self.avisos:
            print(f"\nAviso: {tabela} tem {total} linhas com {descricao}")
        print()


def sem_acento(texto):
    normalizado = unicodedata.normalize("NFKD", texto)
    return normalizado.encode("ascii", "ignore").decode("ascii")


def ausente(valor):
    """Vazio, só pontuação ("-", "***") ou marcador como "s/n" e "não tem"."""
    if not re.search(r"\w", valor):
        return True
    return bool(MARCADOR_AUSENTE.fullmatch(sem_acento(valor).lower()))


def inteiro(valor):
    """Converte "15", "15.0" e "15,0" em 15; None se não for inteiro >= 0."""
    achado = re.fullmatch(r"(\d+)(?:[.,]0+)?", valor)
    return int(achado.group(1)) if achado else None


def ler_data(valor, formatos):
    for formato in formatos:
        try:
            return datetime.strptime(valor, formato)
        except ValueError:
            pass
    return None


def padronizar_horario(valor):
    """Devolve HH:MM:SS, ou vazio quando o horário não é válido."""
    achado = HORARIO.fullmatch(valor)
    if not achado:
        return ""
    hora, minuto, segundo = (int(parte or 0) for parte in achado.groups())
    if hora > 23 or minuto > 59 or segundo > 59:
        return ""
    return f"{hora:02d}:{minuto:02d}:{segundo:02d}"


# ---------------------------------------------------------------------------
# Regras: cada uma recebe o registro (dict), ajusta os valores no lugar e
# devolve o motivo da rejeição quando a linha não pode seguir para o DW.
# ---------------------------------------------------------------------------

def t2_espacos(registro):
    for campo, valor in registro.items():
        registro[campo] = ESPACOS.sub(" ", INVISIVEIS.sub("", valor)).strip()


def t3_ausentes(registro):
    for campo in OPCIONAIS:
        valor = registro[campo]
        so_zeros = campo in ("numero", "complemento") and set(valor) == {"0"}
        if ausente(valor) or so_zeros:
            registro[campo] = ""


def t4_categorias_doacao(registro):
    registro["uf"] = registro["uf"].upper()
    registro["tipo_ong"] = registro["tipo_ong"].upper()
    # o DML casa o município pelo nome em maiúsculas e sem acento
    registro["municipio"] = sem_acento(registro["municipio"]).upper()
    sexo = sem_acento(registro["sexo"]).lower()
    if sexo in SEXOS:
        registro["sexo"] = SEXOS[sexo]
    elif ausente(registro["sexo"]):
        # dim_doador.sexo é NOT NULL: sem rótulo, a doação sairia do fato
        registro["sexo"] = "Não informado"
    primeira = sem_acento(registro["primeira_doacao"]).lower()
    registro["primeira_doacao"] = SIM_NAO.get(
        primeira, registro["primeira_doacao"])
    if registro["uf"] not in SIGLAS:
        return f"UF desconhecida: {registro['uf']!r}"
    if registro["primeira_doacao"] not in ("Sim", "Não"):
        return f"primeira_doacao inválida: {registro['primeira_doacao']!r}"
    if not registro["item"] or not registro["grupo_item"]:
        return "item ou grupo_item em branco"
    return None


def t4_uf(registro):
    registro["uf"] = registro["uf"].upper()


def t5_datas_doacao(registro):
    data = ler_data(registro["data_inversa"], ("%d/%m/%Y", "%Y-%m-%d"))
    if data is None:
        return f"data inválida: {registro['data_inversa']!r}"
    # dd/mm/aaaa é o formato que o DML espera
    registro["data_inversa"] = data.strftime("%d/%m/%Y")
    registro["dia_semana"] = DIAS_SEMANA[data.weekday()]
    registro["horario"] = padronizar_horario(registro["horario"])
    return None


def t5_data_atualizacao(registro):
    if ler_data(registro["data_atualizacao"][:10], ("%Y-%m-%d",)) is None:
        registro["data_atualizacao"] = ""


def t6_numeros_doacao(registro):
    idade, quantidade = inteiro(registro["idade"]), inteiro(registro["qtd"])
    if idade is None or idade > 120:
        return f"idade inválida: {registro['idade']!r}"
    if quantidade is None:
        return f"quantidade inválida: {registro['qtd']!r}"
    registro["idade"], registro["qtd"] = str(idade), str(quantidade)
    return None


def t6_codigos_municipio(registro):
    if not re.fullmatch(r"\d{7}", registro["ibge_code"]):
        return f"código IBGE inválido: {registro['ibge_code']!r}"
    if registro["capital"] not in ("0", "1"):
        return f"indicador de capital fora de 0/1: {registro['capital']!r}"
    return None


def t7_localizacao(registro, municipios):
    """municipios: 6 primeiros dígitos do código IBGE -> (nome, UF)."""
    nome, uf = municipios.get(registro["ibge"][:6], ("", ""))
    registro["uf"] = registro["uf"] or uf
    registro["cidade"] = registro["cidade"] or nome
    cep = re.sub(r"\D", "", registro["cep"])
    if len(cep) == 7 and registro["uf"] == "SP":
        # só os CEPs paulistas começam com zero, que planilhas descartam
        cep = "0" + cep
    registro["cep"] = cep if len(cep) == 8 else ""
    coordenadas = registro["georef_location"].replace("\\", "")
    registro["georef_location"] = coordenadas


def t8_identificador(registro):
    if not registro["id_equipamento"]:
        return "id_equipamento em branco"
    return None


def t8_duplicados(registros, chave):
    """Uma linha por chave (a atualização mais recente) ou por conteúdo."""
    unicos = {}
    for registro in registros:
        identidade = registro[chave] if chave else tuple(registro.values())
        data = registro.get("data_atualizacao", "")
        mantido = unicos.get(identidade)
        if mantido is None or data > mantido.get("data_atualizacao", ""):
            unicos[identidade] = registro
    return list(unicos.values())


def regras_de(tabela, municipios):
    if tabela == "stg_municipios":
        return [("T2", t2_espacos), ("T6", t6_codigos_municipio)]
    if tabela == "stg_doacoes":
        return [
            ("T2", t2_espacos), ("T4", t4_categorias_doacao),
            ("T5", t5_datas_doacao), ("T6", t6_numeros_doacao),
        ]
    return [
        ("T2", t2_espacos), ("T3", t3_ausentes), ("T4", t4_uf),
        ("T5", t5_data_atualizacao),
        ("T7", partial(t7_localizacao, municipios=municipios)),
        ("T8", t8_identificador),
    ]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def colunas_staging():
    """Layout das tabelas de staging, lido do DDL para nunca divergir dele."""
    conexao = sqlite3.connect(":memory:")
    try:
        conexao.executescript(DDL_STAGING.read_text(encoding="utf-8"))
        return {
            tabela: [coluna[1] for coluna in
                     conexao.execute(f"PRAGMA table_info({tabela})")]
            for tabela in FONTES
        }
    finally:
        conexao.close()


def extrair(tabela, colunas):
    """T1: lê a fonte como texto e confere o cabeçalho com o staging."""
    arquivo, separador, _ = FONTES[tabela]
    with open(arquivo, newline="", encoding="utf-8-sig") as f:
        leitor = csv.reader(f, delimiter=separador)
        cabecalho = [sem_acento(nome).strip().lower() for nome in next(leitor)]
        if cabecalho != colunas:
            raise ValueError(
                f"{arquivo.name}: cabeçalho {cabecalho} "
                f"diferente do staging {colunas}")
        return list(leitor)


def transformar(tabela, colunas, linhas, municipios, qualidade):
    """Aplica T2 a T7 em cada linha e T8 no conjunto das aceitas."""
    regras = regras_de(tabela, municipios)
    aceitos = []
    for numero, linha in enumerate(linhas, start=1):
        rejeicao = None
        if len(linha) != len(colunas):
            rejeicao = ("T1", "quantidade de campos diferente do layout")
        else:
            registro = dict(zip(colunas, linha))
            for codigo, regra in regras:
                antes = dict(registro)
                motivo = regra(registro)
                if motivo:
                    rejeicao = (codigo, motivo)
                    break
                if registro != antes:
                    qualidade.alteradas[tabela, codigo] += 1
        if rejeicao:
            qualidade.rejeitados.append(
                [tabela, numero, *rejeicao, " | ".join(linha)])
        else:
            aceitos.append(registro)
    unicos = t8_duplicados(aceitos, FONTES[tabela][2])
    qualidade.linhas[tabela] = (
        len(linhas), len(unicos),
        len(aceitos) - len(unicos), len(linhas) - len(aceitos))
    return unicos


def gravar(arquivo, cabecalho, linhas):
    with open(arquivo, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)


def gerar_staging(destino=STAGING):
    """Extrai, transforma e grava o staging; devolve {tabela: arquivo}."""
    qualidade = Qualidade()
    municipios = {}
    arquivos = {}
    destino.mkdir(parents=True, exist_ok=True)
    for tabela, colunas in colunas_staging().items():
        linhas = extrair(tabela, colunas)
        registros = transformar(tabela, colunas, linhas, municipios, qualidade)
        if tabela == "stg_municipios":
            for r in registros:
                uf = UF_POR_CODIGO.get(r["codigo_uf"], "")
                municipios[r["ibge_code"][:6]] = (r["municipio"], uf)
        if tabela == "stg_doacoes":
            degradados = sum("E+" in r["id_ong"].upper() for r in registros)
            if degradados:
                qualidade.avisos.append((tabela, degradados, AVISO_ID_ONG))
        arquivos[tabela] = destino / f"{tabela}.csv"
        gravar(arquivos[tabela], colunas, [r.values() for r in registros])
    gravar(destino / "rejeitados.csv",
           ["tabela", "registro", "regra", "motivo", "conteudo"],
           qualidade.rejeitados)
    qualidade.imprimir()
    return arquivos


if __name__ == "__main__":
    gerar_staging()
