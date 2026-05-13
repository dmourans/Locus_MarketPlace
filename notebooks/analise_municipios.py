#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(style="whitegrid")

# Load the processed municipalities data
df = pd.read_csv("../data/processed/municipios_tratado.csv")

# Filter for São Paulo state (codigo_uf = 35)
df_sp = df[df["codigo_uf"] == 35]
print("First 5 rows of São Paulo municipalities:")
print(df_sp.head())

# Count number of municipalities by DDD (area code)
ddd_sp = (
    df_sp.groupby("ddd")["municipio"]
    .count()
    .reset_index()
)
ddd_sp.columns = ["ddd", "municipio"]  # Rename columns for clarity

print("\nMunicipality count by DDD:")
print(ddd_sp)

# Create bar plot
plt.figure(figsize=(10, 6))

sns.barplot(
    data=ddd_sp,
    x="ddd",
    y="municipio"
)

plt.title("Quantidade de Municípios por DDD no Estado de São Paulo")
plt.xlabel("DDD")
plt.ylabel("Número de Municípios")

plt.tight_layout()
plt.show()