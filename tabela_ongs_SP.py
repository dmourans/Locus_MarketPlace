#  FONTE PRINCIPAL DOS DADOS: Mapa das Organizações da Sociedade Civil (OSCs)
#  https://mapaosc.ipea.gov.br/base-dados

import pandas as pd

df = pd.read_csv('20260226_MOSC_baseresumida.csv', sep=';', encoding='latin1')


#  REMOVENDO COLUNAS QUE NÃO SERÃO UTILIZADAS
df = df = df.drop(columns=[       
        'Area_Associacoes_patronais_e_profissionais', 'cnae_secundaria',
        'Area_Cultura_e_recreacao', 'cd_municipio',
        'Area_Desenvolvimento_e_defesa_de_direitos_e_interesses',
        'Area_Educacao_e_pesquisa', 'Area_Outras_atividades_associativas',
        'Area_Religiao', 'Area_Saude', 'SubArea_Assistencia_social',
        'SubArea_Associacoes_de_atividades_nao_especificadas_anteriormente',
        'SubArea_Associacoes_de_produtores_rurais_pescadores_e_similares',
        'SubArea_Associacoes_empresariais_e_patronais', 'situacao_cadastral',
        'SubArea_Associacoes_profissionais', 'matriz_filial', 'situacao_cadastral',
        'SubArea_Atividades_de_apoio_a_educacao', 'SubArea_Cultura_e_arte',
        'SubArea_Desenvolvimento_e_defesa_de_direitos',
        'SubArea_Educacao_infantil', 'SubArea_Educacao_profissional',
        'SubArea_Ensino_fundamental', 'SubArea_Ensino_superior',
        'SubArea_Esportes_e_recreacao', 'SubArea_Estudos_e_pesquisas',
        'SubArea_Hospitais', 'SubArea_Outras_formas_de_educacao_ensino',
        'SubArea_Outros_servicos_de_saude', 'SubArea_Religiao', 'natureza_juridica'])


#  APLICANDO FILTROS PARA O CONTEXTO DO PROJETO
df = df[(df['UF_Sigla'] == 'SP')]
df = df[(df['Area_Assistencia_social'] == 1.0)]
df = df[df['ano_fechamento'].isna()]


#  SALVANDO ARQUIVOS FINAL
df.to_csv('ONGS_SP.csv', sep=';', index=False, encoding='latin1')