import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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
    if pd.isna(geo):
        return pd.Series([np.nan, np.nan])
    partes = geo.replace('\\', '').split(',')
    if len(partes) == 2:
        return pd.Series([float(partes[0]), float(partes[1])])
    return pd.Series([np.nan, np.nan])

# CARREGAMENTO DOS DADOS

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

    # Consolidar por município
    ongs_por_municipio = ongs_sp.groupby('municipio_norm').size().reset_index(name='num_ongs')
    cras_por_municipio = cras_sp.groupby('cidade_norm').size().reset_index(name='num_cras')
    creas_por_municipio = creas_sp.groupby('cidade_norm').size().reset_index(name='num_creas')
    doacoes_por_municipio = doacoes2024_sp.groupby('municipio_norm').size().reset_index(name='num_doacoes')

    df_municipios = ongs_por_municipio.copy()
    df_municipios = pd.merge(df_municipios, cras_por_municipio, left_on='municipio_norm', right_on='cidade_norm', how='left')
    df_municipios.drop(columns=['cidade_norm'], errors='ignore', inplace=True)
    df_municipios = pd.merge(df_municipios, creas_por_municipio, left_on='municipio_norm', right_on='cidade_norm', how='left')
    df_municipios.drop(columns=['cidade_norm'], errors='ignore', inplace=True)
    df_municipios = pd.merge(df_municipios, doacoes_por_municipio, on='municipio_norm', how='left')
    df_municipios[['num_ongs','num_cras','num_creas','num_doacoes']] = df_municipios[['num_ongs','num_cras','num_creas','num_doacoes']].fillna(0).astype(int)

    return df_municipios, ongs_sp, municipios


df_municipios, ongs_sp, municipios = carregar_dados()

# SIDEBAR 

#st.sidebar.image("https://via.placeholder.com/200x60?text=Locus+MarketPlace", width=200)
st.sidebar.title("🌱 Locus MarketPlace")
pagina = st.sidebar.radio("", ["🏠 Visão Geral", "📊 Análise Descritiva", "🗺️ Municípios por DDD"])

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
    st.dataframe(df_municipios.rename(columns={
        'municipio_norm': 'Município',
        'num_ongs': 'ONGs',
        'num_cras': 'CRAS',
        'num_creas': 'CREAS',
        'num_doacoes': 'Doações 2024'
    }), use_container_width=True)

# PÁGINA 2

elif pagina == "📊 Análise Descritiva":
    st.title("📊 Análise Descritiva")
    st.divider()

    # Top N filtro
    top_n = st.slider("Número de municípios no ranking", 5, 20, 10)

    # Gráfico 1 - Top ONGs
    st.subheader("🏆 Top Municípios por ONGs")
    top_ongs = df_municipios.nlargest(top_n, 'num_ongs')
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top_ongs, y='municipio_norm', x='num_ongs', palette='viridis', ax=ax)
    ax.set_xlabel('Número de ONGs')
    ax.set_ylabel('Município')
    st.pyplot(fig)
    plt.close()

    st.divider()

    # Gráfico 2 - ONGs x CRAS x CREAS
    st.subheader("📊 Comparativo: ONGs, CRAS e CREAS")
    top10 = df_municipios.nlargest(10, 'num_ongs').sort_values('num_ongs', ascending=False)
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(top10))
    width = 0.25
    ax.bar(x - width, top10['num_ongs'],  width, label='ONGs',  color='#2ecc71')
    ax.bar(x,          top10['num_cras'],  width, label='CRAS',  color='#3498db')
    ax.bar(x + width,  top10['num_creas'], width, label='CREAS', color='#e74c3c')
    ax.set_xticks(x)
    ax.set_xticklabels(top10['municipio_norm'], rotation=45, ha='right')
    ax.legend()
    ax.set_title('ONGs, CRAS e CREAS — Top 10 Municípios')
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.divider()

    # Gráfico 3 - Vulnerabilidade
    st.subheader("⚠️ Indicador de Vulnerabilidade")
    df_municipios['doacoes_por_ong'] = df_municipios['num_doacoes'] / (df_municipios['num_ongs'] + 1)
    top_vulneraveis = df_municipios.nlargest(top_n, 'doacoes_por_ong')
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top_vulneraveis, y='municipio_norm', x='doacoes_por_ong', palette='coolwarm', ax=ax)
    ax.set_xlabel('Doações por ONG (razão)')
    ax.set_ylabel('Município')
    st.pyplot(fig)
    plt.close()

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
        plt.close()

    with col2:
        st.subheader("📋 Tabela")
        st.dataframe(ddd_sp, use_container_width=True)