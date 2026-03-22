# -------------------------------
# IMPORTS
# -------------------------------
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re
import time

from steam_market_api import pegar_preco


# -------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -------------------------------
st.set_page_config(
    page_title="Steam Market Analyzer",
    layout="wide"
)

st.title("🎮 Steam Market Analyzer")


# -------------------------------
# INPUT DO USUÁRIO
# -------------------------------
# Área para colar links
links = st.text_area("Cole os links dos itens da Steam (um por linha)")

# Seleção de moeda
moeda = st.selectbox("Escolha a moeda", ["USD", "BRL"])

# Código da moeda usado na API
currency_code = 1 if moeda == "USD" else 7


# -------------------------------
# FUNÇÃO: LIMPEZA DE PREÇO
# -------------------------------
def limpar_preco(preco):
    """
    Converte string de preço (ex: 'R$ 1.234,56')
    para float (1234.56)
    """

    preco = preco.replace("R$", "").replace("$", "").strip()

    if "," in preco:
        preco = preco.replace(".", "").replace(",", ".")
    else:
        preco = preco.replace(",", "")

    numeros = re.findall(r"\d+\.?\d*", preco)

    if numeros:
        return float(numeros[0])

    return 0


# -------------------------------
# BOTÃO PRINCIPAL
# -------------------------------
if st.button("Analisar"):

    # Separar links por linha
    lista_links = links.split("\n")

    resultados = []

    # Loading visual
    with st.spinner("Buscando dados no mercado da Steam..."):

        for link in lista_links:

            link = link.strip()

            # Ignorar linhas vazias
            if link == "":
                continue

            # Consulta API
            dados = pegar_preco(link, currency_code)

            # Delay para evitar bloqueio da API
            time.sleep(1)

            if dados:
                resultados.append(dados)

    # -------------------------------
    # VALIDAÇÃO DE RESULTADO
    # -------------------------------
    if len(resultados) == 0:
        st.error("Não foi possível obter dados da Steam.")

    else:
        # Criar DataFrame
        df = pd.DataFrame(resultados)

        # -------------------------------
        # TRATAMENTO DE DADOS
        # -------------------------------
        df["Preço atual num"] = df["Preço atual"].apply(limpar_preco)
        df["Preço mediano num"] = df["Preço mediano"].apply(limpar_preco)

        df["Diferença"] = df["Preço atual num"] - df["Preço mediano num"]

        df["Variação %"] = (
            df["Diferença"] / df["Preço mediano num"] * 100
        ).round(2)

        # -------------------------------
        # TABELA
        # -------------------------------
        st.subheader("📋 Tabela de análise")

        st.dataframe(
            df[["Item", "Preço atual", "Preço mediano", "Volume 24h", "Variação %"]],
            use_container_width=True
        )

        # -------------------------------
        # GRÁFICO (VERSÃO MELHORADA)
        # -------------------------------
        st.subheader("📊 Variação de preço em relação à mediana")

        fig, ax = plt.subplots(figsize=(10, 6))

        # Fundo transparente (dark mode)
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")

        # Cores mais suaves
        cores = [
            "#4CAF50" if x > 0 else "#F44336"
            for x in df["Variação %"]
        ]

        ax.bar(df["Item"], df["Variação %"], color=cores)

        # Linha zero
        ax.axhline(0, linewidth=1)

        # Título e labels
        ax.set_title("Variação percentual do preço", color="white")
        ax.set_ylabel("Variação (%)", color="white")

        # Eixos
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')

        # Grid leve
        ax.grid(axis='y', linestyle='--', alpha=0.3)

        # Rotação labels
        plt.xticks(rotation=90)

        plt.tight_layout()

        st.pyplot(fig)
