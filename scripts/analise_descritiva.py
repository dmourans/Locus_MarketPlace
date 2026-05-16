#!/usr/bin/env python
# coding: utf-8

"""
O código apresentado realiza uma análise descritiva e exploratória de dados relacionados a assistência social (CRAS e CREAS), doações e ONGs nas 100 cidades mais populosas estado de São Paulo.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from folium.plugins import HeatMap
import unicodedata
import nbformat
import base64
import markdown
import os

import warnings
warnings.filterwarnings('ignore')  # Manter visual de saída clean para dar mais foco no conteúdo

# Configurar visualização
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)

# Carregar os arquivos CSV
cras = pd.read_csv('../data/raw/CRAS_BRASIL.csv')
creas = pd.read_csv('../data/raw/CREAS_BRASIL.csv')
doacoes2024 = pd.read_csv('../data/raw/doações2024.csv', sep=';', encoding='latin1')
doacoes2025 = pd.read_csv('../data/raw/doadores2025.csv', sep=';', encoding='latin1')
ongs = pd.read_csv('../data/raw/ONGS_SP_TOP100_POP.csv', sep=';', encoding='latin1')

# Filtrar CRAS e CREAS de SP
cras_sp = cras[cras['uf'] == 'SP'].copy()
creas_sp = creas[creas['uf'] == 'SP'].copy()

# Filtrar doações de SP
doacoes2024_sp = doacoes2024[doacoes2024['uf'] == 'SP'].copy()
doacoes2025_sp = doacoes2025[doacoes2025['uf'] == 'SP'].copy()

# ONGs já são de SP
ongs_sp = ongs.copy()

print(ongs_sp.columns.tolist())

# Função para converter string com vírgula decimal para float
def convert_decimal(v):
    if pd.isna(v):
        return np.nan
    return float(str(v).replace(',', '.'))

# Doações 2024
doacoes2024_sp['latitude'] = pd.to_numeric(doacoes2024_sp['latitude'], errors='coerce') / 1e7
doacoes2024_sp['longitude'] = pd.to_numeric(doacoes2024_sp['longitude'], errors='coerce') / 1e7

# Doações 2025
doacoes2025_sp['latitude'] = doacoes2025_sp['latitude'].apply(convert_decimal)
doacoes2025_sp['longitude'] = doacoes2025_sp['longitude'].apply(convert_decimal)

# ONGs SP
ongs_sp['latitude'] = ongs_sp['latitude'].apply(convert_decimal)
ongs_sp['longitude'] = ongs_sp['longitude'].apply(convert_decimal)

# CRAS SP: extrair de georef_location
def extrair_lat_lon(geo):
    if pd.isna(geo):
        return pd.Series([np.nan, np.nan])
    # Formato: "-19.300450798730797\,-43.21974277496338"
    partes = geo.replace('\\', '').split(',')
    if len(partes) == 2:
        return pd.Series([float(partes[0]), float(partes[1])])
    else:
        return pd.Series([np.nan, np.nan])

cras_sp[['latitude', 'longitude']] = cras_sp['georef_location'].apply(extrair_lat_lon)

# CREAS SP
creas_sp[['latitude', 'longitude']] = creas_sp['georef_location'].apply(extrair_lat_lon)

print('Conversão de coordenadas concluída.')

# Função para padronizar nomes (maiúsculas, remover acentos)
def normalize_city(name):
    if pd.isna(name):
        return name
    name = str(name).upper().strip()
    # Remover acentos
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    return name

# Aplicar nos DataFrames
cras_sp['cidade_norm'] = cras_sp['cidade'].apply(normalize_city)
creas_sp['cidade_norm'] = creas_sp['cidade'].apply(normalize_city)
ongs_sp['municipio_norm'] = ongs_sp['municipio_nome'].apply(normalize_city)
doacoes2024_sp['municipio_norm'] = doacoes2024_sp['municipio'].apply(normalize_city)

# Contagem de ONGs por município
ongs_por_municipio = ongs_sp.groupby('municipio_norm').size().reset_index(name='num_ongs')

# Contagem de CRAS por município
cras_por_municipio = cras_sp.groupby('cidade_norm').size().reset_index(name='num_cras')

# Contagem de CREAS por município
creas_por_municipio = creas_sp.groupby('cidade_norm').size().reset_index(name='num_creas')

# Contagem de doações (2024) por município
doacoes_por_municipio = doacoes2024_sp.groupby('municipio_norm').size().reset_index(name='num_doacoes')

# Unir tudo a partir da base de ONGs (apenas municípios que possuem ONGs)
df_municipios = ongs_por_municipio.copy()

# Merge com CRAS (left join)
df_municipios = pd.merge(df_municipios, cras_por_municipio, 
                         left_on='municipio_norm', right_on='cidade_norm', 
                         how='left')
df_municipios.drop(columns=['cidade_norm'], errors='ignore', inplace=True)

# Merge com CREAS (left join)
df_municipios = pd.merge(df_municipios, creas_por_municipio, 
                         left_on='municipio_norm', right_on='cidade_norm', 
                         how='left')
df_municipios.drop(columns=['cidade_norm'], errors='ignore', inplace=True)

# Merge com doações (left join)
df_municipios = pd.merge(df_municipios, doacoes_por_municipio, 
                         on='municipio_norm', how='left')

# Preencher NaN com 0 nas colunas numéricas
cols_num = ['num_ongs', 'num_cras', 'num_creas', 'num_doacoes']
df_municipios[cols_num] = df_municipios[cols_num].fillna(0).astype(int)

# Verificar resultado
print(f"Total de municípios com ONGs: {len(df_municipios)}")

# Ordenar por número de ONGs (decrescente)
top_ongs = df_municipios.nlargest(10, 'num_ongs')[['municipio_norm', 'num_ongs']]

# Gráfico de barras horizontais
plt.figure(figsize=(10, 6))
sns.barplot(data=top_ongs, y='municipio_norm', x='num_ongs', palette='viridis')
plt.title('Top 10 Municípios com Maior Número de ONGs em SP')
plt.xlabel('Número de ONGs')
plt.ylabel('Município')
plt.tight_layout()
plt.show()

# Garantir que cada município apareça apenas uma vez (caso haja duplicatas)
df_municipios_unique = df_municipios.groupby('municipio_norm', as_index=False).agg({
    'num_ongs': 'sum',
    'num_cras': 'sum',
    'num_creas': 'sum',
    'num_doacoes': 'sum'
})

# 1. Total de municípios únicos
total_municipios = len(df_municipios_unique)

# 2. Municípios com ZERO ONGs
municipios_sem_ong = df_municipios_unique[df_municipios_unique['num_ongs'] == 0]
quantidade_sem_ong = len(municipios_sem_ong)

print("="*50)
print("MUNICÍPIOS SEM NENHUMA ONG")
print("="*50)
print(f"Total de municípios analisados: {total_municipios}")
print(f"Municípios sem nenhuma ONG: {quantidade_sem_ong} ({quantidade_sem_ong/total_municipios*100:.2f}%)")

if quantidade_sem_ong > 0:
    print("\nLista completa dos municípios sem ONG (ordenados alfabeticamente):")
    lista_sem_ong = municipios_sem_ong[['municipio_norm', 'num_ongs']].sort_values('municipio_norm')
    print(lista_sem_ong.to_string(index=False))
else:
    print("Todos os municípios possuem pelo menos uma ONG.")

print("\n")

# 3. Quantidade de municípios por faixas exclusivas de número de ONGs
menos_50 = df_municipios_unique[df_municipios_unique['num_ongs'] < 50].shape[0]
entre_50_e_100 = df_municipios_unique[(df_municipios_unique['num_ongs'] >= 50) & (df_municipios_unique['num_ongs'] < 100)].shape[0]
mais_100 = df_municipios_unique[df_municipios_unique['num_ongs'] >= 100].shape[0]

print("="*50)
print("QUANTIDADE DE MUNICÍPIOS POR FAIXA DE ONGs")
print("="*50)
print(f"Municípios com menos de 50 ONGs: {menos_50}")
print(f"Municípios com 50 a 99 ONGs: {entre_50_e_100}")
print(f"Municípios com 100 ONGs ou mais: {mais_100}")

# Gráfico de barras para as faixas exclusivas
faixas = ['< 50', '50 - 99', '100+']
quantidades = [menos_50, entre_50_e_100, mais_100]

plt.figure(figsize=(8, 5))
bars = plt.bar(faixas, quantidades, color=['#ff9999', '#66b3ff', '#99ff99'])
plt.title('Distribuição dos Municípios por Número de ONGs', fontsize=14)
plt.xlabel('Faixa de ONGs', fontsize=12)
plt.ylabel('Quantidade de Municípios', fontsize=12)

for bar, valor in zip(bars, quantidades):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, str(valor), 
             ha='center', va='bottom', fontsize=11)

plt.tight_layout()
plt.show()

# Gráfico de Bolhas: ONGs x População (tamanho = doações)
def converter_populacao(valor):
    if pd.isna(valor):
        return np.nan
    valor_str = str(valor).replace('.', '')
    if ',' in valor_str:
        valor_str = valor_str.replace(',', '.')
    try:
        return float(valor_str)
    except:
        return np.nan

# 1. Converter população
ongs_sp['populacao_clean'] = ongs_sp['Populacao'].apply(converter_populacao)

# 2. Agregar por município
populacao_por_municipio = ongs_sp.groupby('municipio_norm')['populacao_clean'].first().reset_index()
populacao_por_municipio.rename(columns={'populacao_clean': 'populacao'}, inplace=True)

# 3. Mesclar com df_municipios
df_bubble = pd.merge(df_municipios, populacao_por_municipio, on='municipio_norm', how='left')
df_bubble['populacao'] = df_bubble['populacao'].fillna(0)

# 4. Converter população para milhões
df_bubble['populacao_milhoes'] = df_bubble['populacao'] / 1_000_000

# 5. Escalonar tamanho das bolhas com raiz quadrada das doações
max_doacoes = df_bubble['num_doacoes'].max()
if max_doacoes == 0:
    max_doacoes = 1
min_size = 20
max_size = 500
df_bubble['size'] = min_size + (np.sqrt(df_bubble['num_doacoes']) / np.sqrt(max_doacoes)) * (max_size - min_size)

# 6. Criar o gráfico
plt.figure(figsize=(12, 8))
scatter = plt.scatter(
    x=df_bubble['num_ongs'],
    y=df_bubble['populacao_milhoes'],
    s=df_bubble['size'],
    alpha=0.6,
    c=df_bubble['num_doacoes'],
    cmap='viridis',
    edgecolors='black',
    linewidth=0.5
)

cbar = plt.colorbar(scatter)
cbar.set_label('Número de Doações (2024)')

plt.xlabel('Número de ONGs por Município')
plt.ylabel('População (milhões de habitantes)')
plt.title('Relação entre ONGs, População e Doações (2024)')

# Ativar escala logarítmica em ambos os eixos
plt.xscale('log')
plt.yscale('log')

# 7. Anotações para os 5 maiores em ONGs e os 5 maiores em doações
top_ongs = df_bubble.nlargest(5, 'num_ongs')
top_doacoes = df_bubble.nlargest(5, 'num_doacoes')
top_combined = pd.concat([top_ongs, top_doacoes]).drop_duplicates()

for _, row in top_combined.iterrows():
    plt.annotate(row['municipio_norm'], 
                 (row['num_ongs'], row['populacao_milhoes']),
                 xytext=(8, 8), textcoords='offset points', fontsize=9,
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

plt.tight_layout()
plt.show()

# 8. Correlação (usando valores originais em milhões)
df_corr_pop = df_bubble[df_bubble['populacao'] > 0]
if len(df_corr_pop) > 1:
    corr_pop = df_corr_pop['num_ongs'].corr(df_corr_pop['populacao'])
    print(f"Correlação entre ONGs e População: {corr_pop:.3f}")
else:
    print("Dados insuficientes para calcular correlação.")

df_municipios['doacoes_por_ong'] = df_municipios['num_doacoes'] / (df_municipios['num_ongs'] + 1)

# Top 10 municípios com maior razão (mais vulneráveis)
top_vulneraveis = df_municipios.nlargest(10, 'doacoes_por_ong')[['municipio_norm', 'num_ongs', 'num_doacoes', 'doacoes_por_ong']]

plt.figure(figsize=(10, 6))
sns.barplot(data=top_vulneraveis, y='municipio_norm', x='doacoes_por_ong', palette='coolwarm')
plt.title('Top 10 Municípios com Maior Razão Doações / (ONGs+1) - Indicador de Vulnerabilidade')
plt.xlabel('Doações por ONG (razão)')
plt.ylabel('Município')
plt.tight_layout()
plt.show()

print(top_vulneraveis)

# Selecionar os 10 municípios com mais ONGs
top10_ongs = df_municipios.nlargest(10, 'num_ongs')[['municipio_norm', 'num_ongs', 'num_cras', 'num_creas']].copy()
top10_ongs.sort_values('num_ongs', ascending=False, inplace=True)

# Plotar barras agrupadas
plt.figure(figsize=(12, 6))
x = np.arange(len(top10_ongs))
width = 0.25

bars1 = plt.bar(x - width, top10_ongs['num_ongs'], width, label='ONGs', color='#2ecc71')
bars2 = plt.bar(x, top10_ongs['num_cras'], width, label='CRAS', color='#3498db')
bars3 = plt.bar(x + width, top10_ongs['num_creas'], width, label='CREAS', color='#e74c3c')

plt.xlabel('Município')
plt.ylabel('Quantidade')
plt.title('Comparação: ONGs, CRAS e CREAS nos 10 Municípios com mais ONGs')
plt.xticks(x, top10_ongs['municipio_norm'], rotation=45, ha='right')
plt.legend()
plt.tight_layout()
plt.show()

# Opcional: tabela com os dados
print(top10_ongs[['municipio_norm', 'num_ongs', 'num_cras', 'num_creas']].to_string(index=False))

def generate_html_report(notebook_path='analise_descritiva.ipynb', output_html='relatorio_analise.html'):
    """
    Lê o notebook atual, extrai células markdown (convertendo para HTML), imagens dos outputs,
    e gera um arquivo HTML estilizado com design moderno e formatação correta.
    """
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    html_parts = []
    html_parts.append('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório de Análise - ONGs em São Paulo</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                background: linear-gradient(135deg, #f5f7fa 0%, #e9edf2 100%);
                color: #1e293b;
                padding: 2rem 1rem;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 2rem;
                box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
                overflow: hidden;
            }
            header {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 3rem 2rem;
                text-align: center;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            header h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; letter-spacing: -0.02em; }
            header p { font-size: 1.1rem; opacity: 0.9; max-width: 700px; margin: 0 auto; }
            .content { padding: 2rem; }
            .analysis {
                background: #ffffff;
                border-radius: 1.5rem;
                margin: 2rem 0;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                border-left: 4px solid #3b82f6;
            }
            .analysis:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
            }
            .analysis h1, .analysis h2, .analysis h3, .analysis h4 {
                margin-top: 1.5rem;
                margin-bottom: 0.75rem;
                font-weight: 600;
                line-height: 1.3;
            }
            .analysis h1 { font-size: 1.8rem; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }
            .analysis h2 { font-size: 1.5rem; color: #1e293b; }
            .analysis h3 { font-size: 1.25rem; color: #334155; }
            .analysis p { margin: 1rem 0; }
            .analysis ul, .analysis ol { margin: 1rem 0 1rem 1.5rem; }
            .analysis li { margin: 0.5rem 0; }
            .analysis code {
                background: #f1f5f9;
                padding: 0.2rem 0.4rem;
                border-radius: 0.375rem;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.875em;
                color: #0f172a;
            }
            .analysis pre {
                background: #f8fafc;
                padding: 1rem;
                border-radius: 0.75rem;
                overflow-x: auto;
                border: 1px solid #e2e8f0;
            }
            .plot {
                background: #f8fafc;
                border-radius: 1rem;
                margin: 2rem 0;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .plot:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
            }
            .plot img {
                max-width: 100%;
                height: auto;
                border-radius: 0.5rem;
                background: white;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }
            hr { border: none; border-top: 1px solid #e2e8f0; margin: 2rem 0; }
            footer {
                background: #f1f5f9;
                text-align: center;
                padding: 1.5rem;
                color: #475569;
                font-size: 0.875rem;
                border-top: 1px solid #e2e8f0;
            }
            @media (max-width: 768px) {
                .content { padding: 1rem; }
                .analysis, .plot { padding: 1rem; }
                header h1 { font-size: 1.8rem; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>📊 Relatório de Análise</h1>
                <p>ONGs, Doações e Equipamentos Sociais nas 100 cidades mais populosas de São Paulo</p>
            </header>
            <div class="content">
    ''')

    for cell in nb.cells:
        if cell.cell_type == 'markdown':
            # Converte markdown para HTML com extensões para listas e tabelas
            html_content = markdown.markdown(cell.source, extensions=['extra', 'sane_lists'])
            html_parts.append(f'<div class="analysis">\n{html_content}\n</div>')
        elif cell.cell_type == 'code':
            for output in cell.outputs:
                if output.output_type == 'display_data' and 'image/png' in output.data:
                    img_data = output.data['image/png']
                    html_parts.append(f'<div class="plot"><img src="data:image/png;base64,{img_data}" alt="Gráfico"></div>')
                elif output.output_type == 'stream' and 'text' in output:
                    text = output.text.strip()
                    # Mantém apenas prints de resultados importantes (evita logs de conversão)
                    if text and not text.startswith('Conversão') and not text.startswith('Total de municípios'):
                        if 'Correlação' in text or 'Municípios sem nenhuma ONG' in text or 'Top 10' in text:
                            html_parts.append(f'<pre class="analysis" style="background:#f8fafc; padding:1rem; border-radius:0.75rem;"><code>{text}</code></pre>')

    html_parts.append(f'''
            </div>
            <footer>
                Relatório gerado automaticamente a partir da análise descritiva.<br>
                Dados: CRAS, CREAS, Doações 2024/2025 e ONGs nas 100 cidades mais populosas de SP.<br>
                📅 Gerado em {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}
            </footer>
        </div>
    </body>
    </html>
    ''')

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))

    print(f"✅ Relatório HTML gerado: {output_html}")

# Executar a geração
generate_html_report()