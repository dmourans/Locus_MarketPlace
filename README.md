# 🤝 Locus MarketPlace — Conectando Doadores, Centros de Doação e Pessoas Carentes

> Projeto acadêmico desenvolvido para a disciplina de **PROJETO INTEGRADOR: CIÊNCIA DE DADOS APLICADA A SITUAÇÕES DE MERCADO**  
> SENAC EAD — Banco de Dados

## 📌 Sobre o Projeto

O **Locus MarketPlace** é uma iniciativa de análise e visualização de dados voltada para facilitar a comunicação entre:

- 🧑‍🤝‍🧑 **Doadores** — pessoas físicas ou jurídicas que desejam contribuir
- 🏢 **Centros de Doação** — CRAS, CREAS e ONGs cadastradas
- ❤️ **Pessoas em Situação de Vulnerabilidade** — beneficiários dos serviços de assistência social


## 📂 Estrutura do Repositório

```
Locus_Marketplace
├── data/
│   └── processed/
│   │   └── municipios_tratado.py
│   └──raw/
│       ├── CRAS_BRASIL.csv
│       ├── CREAS_BRASIL.csv
│       ├── ONGS_SP.csv
│       ├── doadores2025.csv
│       └── doações2024.csv
├── notebooks/
│   └── analise_municipios.ipynb
├── scripts/
│   └── municipios_brasileiros
│   └── tabela_ongs_SP.py  
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🗃️ Fontes de Dados

| Dataset | Fonte | Descrição |
|---|---|---|
| `CRAS_BRASIL.csv` | [MDS / dados.gov.br](https://dados.gov.br) | Centros de Referência de Assistência Social |
| `CREAS_BRASIL.csv` | [MDS / dados.gov.br](https://dados.gov.br) | Centros de Referência Especializados |
| `ONGS_SP.csv` | Secretaria de Desenvolvimento Social SP | ONGs ativas no estado de SP |
| `doadores2025.csv` | Dados próprios / simulados | Perfil de doadores cadastrados |
| `doações2024.csv` | Dados próprios / simulados | Histórico de doações realizadas |

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **Pandas** — manipulação e análise de dados
- **NumPy** — operações numéricas
- **Matplotlib** — visualizações gráficas
- **Jupyter Notebook / Google Colab** — ambiente de desenvolvimento

## ▶️ Como Executar

### 1. Clone o repositório

```bash
git clone https://github.com/dmourans/Locus_MarketPlace.git
cd <nome-do-repo>
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Execute o notebook

```bash
jupyter notebook analise_municipios.ipynb
```

## 👥 Integrantes do Grupo

| Nome | GitHub |

| Pamela Soares | [@PaamSoares](https://github.com/PaamSoares) |

| Mateus Fernandes | [@mateusfeoliveira](https://github.com/mateusfeoliveira) |

| Deivid Nogueira | [@dmourans](https://github.com/dmourans) |

| Antônio Carlos | [@ACSJr](https://github.com/ACSJr) |

| Anderson Belarmino | [@Anr30](https://github.com/Anr30) |
## 📄 Licença

Este projeto é de uso acadêmico. Dados públicos utilizados conforme licença aberta do [dados.gov.br](https://dados.gov.br).



