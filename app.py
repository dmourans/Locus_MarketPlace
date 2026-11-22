import sqlite3
import re
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import seaborn as sns
import unicodedata
import warnings

warnings.filterwarnings('ignore')
# Configuração da página
st.set_page_config(
    page_title="Locus MarketPlace",
    page_icon="🤝",
    layout="wide"
)
# Estilo
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False
RAIZ = Path(__file__).resolve().parent
ARQUIVO_OLAP = RAIZ / "sql" / "05_olap_operacoes.sql"

def normalize_city(name):
    if pd.isna(name):
        return name
    name = str(name).upper().strip()
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    return name

def convert_decimal(v):
    if pd.isna(v):
        return np.nan
    return float(str(v).replace(',', '.'))

def extrair_lat_lon(geo):
    """Converte o campo georef_location em latitude e longitude.

    Os CSVs de CRAS/CREAS trazem uma barra invertida antes da vírgula
    que separa as coordenadas. Essa barra é removida
    antes da conversão para float. Valores ausentes ou inválidos viram NaN,
    sem interromper o carregamento de toda a aplicação.
    """
    if pd.isna(geo):
        return pd.Series([np.nan, np.nan])

    texto = str(geo).strip().replace("\\", "")
    partes = texto.split(",")
    if len(partes) != 2:
        return pd.Series([np.nan, np.nan])

    try:
        latitude = float(partes[0].strip().strip("()[]"))
        longitude = float(partes[1].strip().strip("()[]"))
    except (TypeError, ValueError):
        return pd.Series([np.nan, np.nan])

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return pd.Series([np.nan, np.nan])

    return pd.Series([latitude, longitude])

# -----------------------------------------------------------------------------
# Data Warehouse: criação automática somente quando necessário
# -----------------------------------------------------------------------------

@st.cache_resource(show_spinner="Preparando o Data Warehouse na primeira abertura...")
def preparar_data_warehouse():
    """Garante que o banco exista e tenha as tabelas necessárias.

    O build_dw.main() apaga e recria o arquivo SQLite. Por isso, ele só é

    chamado quando o banco ainda não existe ou quando o arquivo está inválido.

    O cache de recurso evita repetir a verificação/construção a cada interação

    do usuário no Streamlit.

    """
    from etl.build_dw import BANCO, main as construir_dw
    tabelas_necessarias = {
        "dim_data",
        "dim_uf",
        "dim_municipio",
        "dim_item",
        "dim_doador",
        "dim_unidade",
        "fato_doacao",
        "fato_unidade_assistencial",
    }

    def banco_valido():
        if not BANCO.exists():
            return False
        try:
            with sqlite3.connect(str(BANCO)) as conexao:
                tabelas = {
                    linha[0]
                    for linha in conexao.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                return tabelas_necessarias.issubset(tabelas)
        except sqlite3.Error:
            return False
    codigo_construcao = 0
    if not banco_valido():
        codigo_construcao = construir_dw()
    if not banco_valido():
        raise RuntimeError(
            "O processo ETL terminou, mas as tabelas esperadas não foram "
            "encontradas no banco sql/locus_dw.db."
        )
    return {
        "banco": str(BANCO),
        "houve_divergencia_na_conferencia": codigo_construcao != 0,
    }

@st.cache_data(show_spinner=False)
def carregar_consultas_olap():
    """Lê e separa as dez consultas numeradas no arquivo SQL do projeto."""
    if not ARQUIVO_OLAP.exists():
        raise FileNotFoundError(
            f"Arquivo de consultas não encontrado: {ARQUIVO_OLAP.relative_to(RAIZ)}"
        )
    conteudo = ARQUIVO_OLAP.read_text(encoding="utf-8")
    marcadores = list(
        re.finditer(r"(?m)^--\s*(\d+)\.\s*(.+?)\s*$", conteudo)
    )
    if len(marcadores) != 10:
        raise ValueError(
            "O arquivo sql/05_olap_operacoes.sql deveria conter 10 consultas "
            f"numeradas; foram encontrados {len(marcadores)} marcadores."
        )
    consultas = {}
    for indice, marcador in enumerate(marcadores):
        inicio = marcador.end()
        fim = marcadores[indice + 1].start() if indice + 1 < len(marcadores) else len(conteudo)
        sql = conteudo[inicio:fim]
        sql = re.sub(r"(?m)^\s*--.*$", "", sql).strip()
        sql = sql.rstrip(";").strip() + ";"
        numero = int(marcador.group(1))
        titulo = marcador.group(2).strip()
        if not sql or sql == ";":
            raise ValueError(f"A consulta {numero} ({titulo}) está vazia.")
        consultas[numero] = {"titulo": titulo, "sql": sql}
    return consultas

def consultar_data_warehouse(sql):
    """Executa uma consulta no SQLite e devolve o resultado em DataFrame."""
    from etl.build_dw import BANCO
    with sqlite3.connect(str(BANCO)) as conexao:
        return pd.read_sql_query(sql, conexao)

def formatar_inteiro(valor):
    return f"{int(valor):,}".replace(",", ".")

def formatar_numero_br(valor):
    """Formata números completos no padrão brasileiro, sem abreviar valores."""
    if pd.isna(valor):
        return ""
    numero = float(valor)
    if numero.is_integer():
        formatado = f"{numero:,.0f}"
    else:
        formatado = f"{numero:,.2f}"
    return formatado.replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_numero_compacto(valor):
    """Abrevia números grandes para caber nos rótulos dos gráficos."""
    if pd.isna(valor):
        return ""
    numero = float(valor)
    absoluto = abs(numero)
    if absoluto >= 1_000_000:
        return f"{numero / 1_000_000:.1f}".replace(".", ",") + " mi"
    if absoluto >= 1_000:
        return f"{numero / 1_000:.1f}".replace(".", ",") + " mil"
    return formatar_numero_br(numero)

def renderizar_pagina_olap(status_dw, erro_dw):
    st.title("🧠 Data Warehouse e OLAP")
    st.markdown(
        "Explore os dados consolidados do Locus MarketPlace por meio de "
        "dez operações analíticas. Os resultados são executados diretamente "
        "sobre o Data Warehouse em SQLite."
    )
    st.divider()
    if erro_dw is not None:
        st.error("Não foi possível preparar o Data Warehouse automaticamente.")
        st.code(str(erro_dw))
        st.info(
            "Confira se os arquivos de origem utilizados pelo ETL estão presentes "
            "nas pastas data/raw e data/processed."
        )
        return
    if status_dw and status_dw.get("houve_divergencia_na_conferencia"):
        st.warning(
            "O banco foi criado, mas a conferência do ETL apontou diferença entre "
            "a quantidade de registros de origem e a quantidade carregada nos fatos. "
            "Os resultados abaixo refletem os registros efetivamente carregados."
        )
    try:
        resumo = consultar_data_warehouse(
            """

            SELECT

                COUNT(*) AS registros,

                COALESCE(SUM(qtd), 0) AS itens,

                COUNT(DISTINCT sk_municipio) AS municipios

            FROM fato_doacao

            """
        )
        grupos = consultar_data_warehouse(
            "SELECT COUNT(DISTINCT grupo_item) AS total FROM dim_item"
        )
        consultas = carregar_consultas_olap()
    except Exception as erro:
        st.error("Não foi possível consultar o Data Warehouse ou ler o arquivo OLAP.")
        st.code(str(erro))
        return
    if resumo.empty:
        st.info("O Data Warehouse ainda não possui registros de doações.")
        return
    total_registros = int(resumo.loc[0, "registros"] or 0)
    total_itens = int(resumo.loc[0, "itens"] or 0)
    total_municipios = int(resumo.loc[0, "municipios"] or 0)
    total_grupos = int(grupos.loc[0, "total"] or 0)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros de doação", formatar_inteiro(total_registros))
    col2.metric("Itens doados", formatar_inteiro(total_itens))
    col3.metric("Municípios com doações", formatar_inteiro(total_municipios))
    col4.metric("Grupos de itens", formatar_inteiro(total_grupos))
    st.caption(
        "Os indicadores são calculados a partir das tabelas fato e dimensão do "
        "Data Warehouse. 'Itens doados' representa a soma da quantidade registrada."
    )
    st.divider()
    operacao = st.selectbox(
        "Selecione uma operação OLAP",
        options=list(consultas.keys()),
        format_func=lambda numero: f"{numero:02d} · {consultas[numero]['titulo']}",
        key="selecao_operacao_olap",
    )
    informacoes = {
        1: (
            "Roll-up agrega os dados em níveis mais resumidos: mês, subtotal do "
            "trimestre e total do ano. A tabela mantém os níveis da hierarquia; "
            "o gráfico mostra somente os valores mensais."
        ),
        2: (
            "Drill-down detalha os grupos de itens até chegar aos itens individuais. "
            "O percentual indica quanto cada item representa dentro do próprio grupo."
        ),
        3: (
            "Slice fixa uma dimensão: nesta consulta, o grupo analisado é Alimentação. "
            "Assim, é possível observar a evolução mensal desse grupo."
        ),
        4: (
            "Dice aplica vários filtros ao mesmo tempo: primeiro semestre, grupos "
            "Alimentação e Higiene e doadoras do sexo feminino."
        ),
        5: (
            "Pivot reorganiza os dados: os grupos de itens ficam nas linhas e os "
            "quatro trimestres passam a ser colunas, facilitando a comparação."
        ),
        6: (
            "Cube apresenta as combinações entre grupo de item e trimestre, "
            "incluindo subtotais por grupo, subtotais por trimestre e total geral."
        ),
        7: (
            "Drill-across relaciona duas tabelas fato diferentes: quantidade de itens "
            "doados e quantidade de unidades assistenciais por município."
        ),
        8: (
            "Ranking ordena os dez municípios com maior quantidade de itens recebidos. "
            "A posição é calculada pela soma da quantidade doada."
        ),
        9: (
            "A participação mostra o percentual de cada grupo sobre o total de itens. "
            "O percentual acumulado soma as participações seguindo a ordem do maior "
            "para o menor grupo."
        ),
        10: (
            "O perfil agrupa os registros por faixa etária e pela informação de primeira "
            "doação, apresentando quantidade de registros, itens e média por registro."
        ),
    }
    st.subheader(f"{operacao:02d} · {consultas[operacao]['titulo']}")
    st.write(informacoes.get(operacao, "Resultado da consulta OLAP."))
    try:
        resultado = consultar_data_warehouse(consultas[operacao]["sql"])
    except Exception as erro:
        st.error(f"Erro ao executar a consulta {operacao}: {erro}")
        with st.expander("Ver consulta SQL"):
            st.code(consultas[operacao]["sql"], language="sql")
        return
    if resultado.empty:
        st.info("A consulta foi executada, mas não retornou registros.")
    else:
        if operacao == 1:
            mensal = resultado[
                ~resultado["mes"].str.lower().isin(["subtotal trimestre", "total ano"])
            ].copy()
            ordem_meses = {
                "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
                "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
                "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
            }
            mensal["ordem_mes"] = mensal["mes"].str.lower().map(ordem_meses)
            mensal = mensal.sort_values(["ano", "ordem_mes"])
            mensal["período"] = mensal["mes"].str.capitalize() + " / " + mensal["ano"].astype(str)
            st.markdown("**Evolução mensal das doações**")
            if not mensal.empty:
                fig, ax = plt.subplots(figsize=(12, 5))
                posicoes = np.arange(len(mensal))
                barras = ax.bar(posicoes, mensal["total"])
                ax.set_xticks(posicoes)
                ax.set_xticklabels(mensal["período"], rotation=35, ha="right")
                ax.set_ylabel("Quantidade de itens")
                ax.yaxis.set_major_formatter(
                    FuncFormatter(lambda valor, _: formatar_numero_br(valor))
                )
                ax.grid(axis="y", alpha=0.25)
                ax.set_axisbelow(True)
                # Rótulos compactos sobre as barras para evitar sobreposição.
                for barra, valor in zip(barras, mensal["total"]):
                    altura = barra.get_height()
                    ax.annotate(
                        formatar_numero_compacto(valor),
                        xy=(barra.get_x() + barra.get_width() / 2, altura),
                        xytext=(0, 4),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )
                ax.margins(y=0.18)
                fig.tight_layout()
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            st.markdown("**Hierarquia e totais**")
            tabela_hierarquia = resultado.copy()
            if "total" in tabela_hierarquia.columns:
                tabela_hierarquia["total"] = tabela_hierarquia["total"].map(
                    formatar_numero_br
                )
            st.dataframe(tabela_hierarquia, use_container_width=True)
        elif operacao == 2:
            grupos_disponiveis = sorted(resultado["grupo_item"].dropna().unique().tolist())
            grupo_selecionado = st.selectbox(
                "Grupo de itens", grupos_disponiveis, key="grupo_drilldown"
            )
            detalhamento = resultado[resultado["grupo_item"] == grupo_selecionado].copy()
            principais = detalhamento.nlargest(15, "total").sort_values("total")
            st.markdown(f"**15 itens com maior quantidade no grupo {grupo_selecionado}**")
            st.bar_chart(principais.set_index("item")["total"], use_container_width=True)
            st.dataframe(detalhamento.sort_values("total", ascending=False), use_container_width=True)
        elif operacao == 3:
            resultado = resultado.sort_values("mes")
            st.markdown("**Quantidade mensal de itens do grupo Alimentação**")
            st.line_chart(resultado.set_index("nome_mes")["total"], use_container_width=True)
            st.dataframe(resultado, use_container_width=True)
        elif operacao == 4:
            matriz = resultado.pivot(
                index="trimestre", columns="grupo_item", values="total"
            ).fillna(0)
            matriz.index = [f"{int(x)}º trimestre" for x in matriz.index]
            st.markdown("**Comparação por grupo e trimestre**")
            st.bar_chart(matriz, use_container_width=True)
            st.dataframe(resultado, use_container_width=True)
        elif operacao == 5:
            colunas_trimestre = ["tri_1", "tri_2", "tri_3", "tri_4"]
            st.markdown("**Comparação trimestral por grupo de item**")
            st.bar_chart(
                resultado.set_index("grupo_item")[colunas_trimestre],
                use_container_width=True,
            )
            st.dataframe(resultado, use_container_width=True)
        elif operacao == 6:
            matriz = resultado.pivot(
                index="grupo_item", columns="trimestre", values="total"
            ).fillna(0)
            matriz = matriz.rename(
                columns={"1": "1º tri.", "2": "2º tri.", "3": "3º tri.", "4": "4º tri.", "todos": "Total"}
            )
            st.markdown("**Matriz de combinações e totais**")
            st.dataframe(matriz, use_container_width=True)
        elif operacao == 7:
            st.markdown("**Itens doados por unidade assistencial**")
            grafico = resultado.sort_values("itens_por_unidade", ascending=True)
            st.bar_chart(
                grafico.set_index("municipio")["itens_por_unidade"],
                use_container_width=True,
            )
            st.dataframe(resultado, use_container_width=True)
            st.caption(
                "A razão compara itens doados com o total de unidades CRAS/CREAS "
                "identificadas na consulta para cada município."
            )
        elif operacao == 8:
            st.markdown("**Dez municípios com maior quantidade de itens recebidos**")
            grafico = resultado.sort_values("total", ascending=True)
            st.bar_chart(grafico.set_index("municipio")["total"], use_container_width=True)
            st.dataframe(resultado, use_container_width=True)
        elif operacao == 9:
            st.markdown("**Participação percentual e acumulada por grupo**")
            fig, eixo = plt.subplots(figsize=(11, 5))
            posicoes = np.arange(len(resultado))
            eixo.bar(posicoes, resultado["total"], label="Quantidade de itens")
            eixo.set_ylabel("Quantidade de itens")
            eixo.set_xticks(posicoes)
            eixo.set_xticklabels(resultado["grupo_item"], rotation=35, ha="right")
            eixo2 = eixo.twinx()
            eixo2.plot(
                posicoes,
                resultado["pct_acumulado"],
                marker="o",
                linewidth=2,
                label="Participação acumulada (%)",
            )
            eixo2.set_ylabel("Participação acumulada (%)")
            eixo2.set_ylim(0, 105)
            eixo.set_title("Distribuição e participação acumulada")
            linhas1, rotulos1 = eixo.get_legend_handles_labels()
            linhas2, rotulos2 = eixo2.get_legend_handles_labels()
            eixo.legend(linhas1 + linhas2, rotulos1 + rotulos2, loc="upper left")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            st.dataframe(resultado, use_container_width=True)
        elif operacao == 10:
            ordem_faixas = ["0-17", "18-29", "30-44", "45-59", "60+"]
            resultado["faixa_etaria"] = pd.Categorical(
                resultado["faixa_etaria"], categories=ordem_faixas, ordered=True
            )
            resultado = resultado.sort_values(["faixa_etaria", "primeira_doacao"])
            matriz_itens = resultado.pivot(
                index="faixa_etaria", columns="primeira_doacao", values="itens"
            ).fillna(0)
            st.markdown("**Quantidade de itens por faixa etária e primeira doação**")
            st.bar_chart(matriz_itens, use_container_width=True)
            st.markdown("**Detalhamento do perfil**")
            st.dataframe(resultado, use_container_width=True)
            st.caption(
                "A coluna 'doações' representa a quantidade de registros na tabela fato, "
                "não uma contagem de pessoas únicas. A dimensão doador agrupa perfis "
                "por idade, sexo e primeira doação."
            )
    with st.expander("Ver consulta SQL utilizada"):
        st.code(consultas[operacao]["sql"], language="sql")
# -----------------------------------------------------------------------------

# CARREGAMENTO DOS DADOS EXISTENTES DA APLICAÇÃO
# -----------------------------------------------------------------------------

@st.cache_data
def carregar_dados():
    cras = pd.read_csv('data/raw/CRAS_BRASIL.csv')
    creas = pd.read_csv('data/raw/CREAS_BRASIL.csv')
    doacoes2024 = pd.read_csv('data/raw/doações2024.csv', sep=';', encoding='latin1')
    doacoes2025 = pd.read_csv('data/raw/doadores2025.csv', sep=';', encoding='latin1')
    ongs = pd.read_csv('data/raw/ONGS_SP_TOP100_POP.csv', sep=';', encoding='latin1')
    municipios = pd.read_csv('data/processed/municipios_tratado.csv')
    # Filtrar SP
    cras_sp = cras[cras['uf'] == 'SP'].copy()
    creas_sp = creas[creas['uf'] == 'SP'].copy()
    doacoes2024_sp = doacoes2024[doacoes2024['uf'] == 'SP'].copy()
    ongs_sp = ongs.copy()
    # Coordenadas
    doacoes2024_sp['latitude'] = pd.to_numeric(doacoes2024_sp['latitude'], errors='coerce') / 1e7
    doacoes2024_sp['longitude'] = pd.to_numeric(doacoes2024_sp['longitude'], errors='coerce') / 1e7
    ongs_sp['latitude'] = ongs_sp['latitude'].apply(convert_decimal)
    ongs_sp['longitude'] = ongs_sp['longitude'].apply(convert_decimal)
    cras_sp[['latitude', 'longitude']] = cras_sp['georef_location'].apply(extrair_lat_lon)
    creas_sp[['latitude', 'longitude']] = creas_sp['georef_location'].apply(extrair_lat_lon)
    # Normalizar nomes
    cras_sp['cidade_norm'] = cras_sp['cidade'].apply(normalize_city)
    creas_sp['cidade_norm'] = creas_sp['cidade'].apply(normalize_city)
    ongs_sp['municipio_norm'] = ongs_sp['municipio_nome'].apply(normalize_city)
    doacoes2024_sp['municipio_norm'] = doacoes2024_sp['municipio'].apply(normalize_city)
    # Chave sem acentos para cruzamentos; nome oficial com acentos para exibição.
    # A base de municípios já é utilizada na página de DDD e contém o nome oficial.
    municipios_sp = municipios.loc[municipios['codigo_uf'] == 35, ['municipio']].copy()
    municipios_sp['municipio_norm'] = municipios_sp['municipio'].apply(normalize_city)
    mapa_nomes_municipios = (
        municipios_sp.dropna(subset=['municipio_norm'])
        .drop_duplicates(subset=['municipio_norm'])
        .set_index('municipio_norm')['municipio']
        .to_dict()
    )
    # Consolidar por município
    ongs_por_municipio = ongs_sp.groupby('municipio_norm').size().reset_index(name='num_ongs')
    cras_por_municipio = cras_sp.groupby('cidade_norm').size().reset_index(name='num_cras')
    creas_por_municipio = creas_sp.groupby('cidade_norm').size().reset_index(name='num_creas')
    doacoes_por_municipio = doacoes2024_sp.groupby('municipio_norm').size().reset_index(name='num_doacoes')
    df_municipios = ongs_por_municipio.copy()
    df_municipios = pd.merge(
        df_municipios, cras_por_municipio,
        left_on='municipio_norm', right_on='cidade_norm', how='left'
    )
    df_municipios.drop(columns=['cidade_norm'], errors='ignore', inplace=True)
    df_municipios = pd.merge(
        df_municipios, creas_por_municipio,
        left_on='municipio_norm', right_on='cidade_norm', how='left'
    )
    df_municipios.drop(columns=['cidade_norm'], errors='ignore', inplace=True)
    df_municipios = pd.merge(
        df_municipios, doacoes_por_municipio, on='municipio_norm', how='left'
    )
    df_municipios[['num_ongs', 'num_cras', 'num_creas', 'num_doacoes']] = (
        df_municipios[['num_ongs', 'num_cras', 'num_creas', 'num_doacoes']]
        .fillna(0)
        .astype(int)
    )
    # Recupera a grafia oficial (incluindo ç, ã, õ, é etc.) sem alterar a chave dos joins.
    df_municipios['municipio_exibicao'] = (
        df_municipios['municipio_norm']
        .map(mapa_nomes_municipios)
        .fillna(df_municipios['municipio_norm'])
    )
    return df_municipios, ongs_sp, municipios
# A aplicação tenta preparar o DW na primeira abertura. Se houver falha,
# as três páginas existentes continuam disponíveis; a página OLAP informa o erro.
try:
    status_dw = preparar_data_warehouse()
    erro_dw = None
except Exception as erro:
    status_dw = None
    erro_dw = erro
df_municipios, ongs_sp, municipios = carregar_dados()

# SIDEBAR
st.sidebar.title("🌱 Locus MarketPlace")
pagina = st.sidebar.radio(
    "",
    [
        "🏠 Visão Geral",
        "📊 Análise Descritiva",
        "🗺️ Municípios por DDD",
        "🧠 Data Warehouse e OLAP",
    ],
)

# PÁGINA 1
if pagina == "🏠 Visão Geral":
    st.title("🤝❤️ Locus MarketPlace")
    st.markdown("#### Conectando Doadores, Centros de Doação e Pessoas Carentes")
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Municípios", len(df_municipios))
    col2.metric("Total de ONGs", int(df_municipios['num_ongs'].sum()))
    col3.metric("Total de CRAS", int(df_municipios['num_cras'].sum()))
    col4.metric("Total de CREAS", int(df_municipios['num_creas'].sum()))
    st.divider()
    st.subheader("📋 Tabela de Municípios")
    st.dataframe(
        df_municipios.rename(columns={
            'municipio_exibicao': 'Município',
            'num_ongs': 'ONGs',
            'num_cras': 'CRAS',
            'num_creas': 'CREAS',
            'num_doacoes': 'Doações 2024',
        }).drop(columns=['municipio_norm']),
        use_container_width=True,
    )

# PÁGINA 2
elif pagina == "📊 Análise Descritiva":
    st.title("📊 Análise Descritiva")
    st.divider()
    top_n = st.slider("Número de municípios no ranking", 5, 20, 10)
    st.subheader("🏆 Top Municípios por ONGs")
    top_ongs = df_municipios.nlargest(top_n, 'num_ongs')
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top_ongs, y='municipio_exibicao', x='num_ongs', palette='viridis', ax=ax)
    ax.set_xlabel('Número de ONGs')
    ax.set_ylabel('Município')
    st.pyplot(fig)
    plt.close(fig)
    st.divider()
    st.subheader("📊 Comparativo: ONGs, CRAS e CREAS")
    top10 = df_municipios.nlargest(10, 'num_ongs').sort_values('num_ongs', ascending=False)
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(top10))
    width = 0.25
    ax.bar(x - width, top10['num_ongs'], width, label='ONGs', color='#2ecc71')
    ax.bar(x, top10['num_cras'], width, label='CRAS', color='#3498db')
    ax.bar(x + width, top10['num_creas'], width, label='CREAS', color='#e74c3c')
    ax.set_xticks(x)
    ax.set_xticklabels(top10['municipio_exibicao'], rotation=45, ha='right')
    ax.legend()
    ax.set_title('ONGs, CRAS e CREAS — Top 10 Municípios')
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    st.divider()
    st.subheader("⚠️ Indicador de Vulnerabilidade")
    df_municipios['doacoes_por_ong'] = df_municipios['num_doacoes'] / (df_municipios['num_ongs'] + 1)
    top_vulneraveis = df_municipios.nlargest(top_n, 'doacoes_por_ong')
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top_vulneraveis, y='municipio_exibicao', x='doacoes_por_ong', palette='coolwarm', ax=ax)
    ax.set_xlabel('Doações por ONG (razão)')
    ax.set_ylabel('Município')
    st.pyplot(fig)
    plt.close(fig)

# PÁGINA 3: MUNICÍPIOS POR DDD
elif pagina == "🗺️ Municípios por DDD":
    st.title("🗺️ Municípios por DDD — São Paulo")
    st.divider()
    df_sp = municipios[municipios['codigo_uf'] == 35]
    ddd_sp = df_sp.groupby('ddd')['municipio'].count().reset_index()
    ddd_sp.columns = ['DDD', 'Municípios']
    col1, col2 = st.columns([2, 1])
    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(data=ddd_sp, x='DDD', y='Municípios', ax=ax)
        ax.set_title('Quantidade de Municípios por DDD no Estado de São Paulo')
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    with col2:
        st.subheader("📋 Tabela")
        st.dataframe(ddd_sp, use_container_width=True)

# PÁGINA 4: DATA WAREHOUSE E OLAP (COMMIT 7)
elif pagina == "🧠 Data Warehouse e OLAP":
    renderizar_pagina_olap(status_dw, erro_dw)
