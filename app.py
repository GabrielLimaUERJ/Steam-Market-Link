import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re
import time

from steam_market_api import pegar_preco


st.set_page_config(page_title="Steam Market Analyzer", layout="wide")

st.title("Steam Market Analyzer")

links = st.text_area("Cole os links dos itens da Steam (um por linha)")

moeda = st.selectbox("Escolha a moeda", ["USD", "BRL"])

currency_code = 1 if moeda == "USD" else 7


def limpar_preco(preco):

    preco = preco.replace("R$", "").replace("$", "").strip()

    if "," in preco:
        preco = preco.replace(".", "").replace(",", ".")
    else:
        preco = preco.replace(",", "")

    numeros = re.findall(r"\d+\.?\d*", preco)

    if numeros:
        return float(numeros[0])

    return 0


if st.button("Analisar"):

    lista_links = links.split("\n")

    resultados = []

    with st.spinner("Buscando dados no mercado da Steam..."):

        for link in lista_links:

            link = link.strip()

            if link == "":
                continue

            dados = pegar_preco(link, currency_code)

            time.sleep(1)

            if dados:
                resultados.append(dados)

    if len(resultados) == 0:

        st.error("Não foi possível obter dados da Steam.")

    else:

        df = pd.DataFrame(resultados)

        df["Preço atual num"] = df["Preço atual"].apply(limpar_preco)
        df["Preço mediano num"] = df["Preço mediano"].apply(limpar_preco)

        df["Diferença"] = df["Preço atual num"] - df["Preço mediano num"]

        df["Variação %"] = (df["Diferença"] / df["Preço mediano num"] * 100).round(2)

        st.subheader("Tabela de análise")

        st.dataframe(df[["Item", "Preço atual", "Preço mediano", "Volume 24h", "Variação %"]])

        st.subheader("Variação de preço em relação à mediana")

        fig, ax = plt.subplots()

        cores = ["green" if x > 0 else "red" for x in df["Variação %"]]

        ax.bar(df["Item"], df["Variação %"], color=cores)

        ax.set_title("Variação percentual do preço")

        ax.set_ylabel("Variação (%)")

        ax.axhline(0)

        plt.xticks(rotation=45)

        st.pyplot(fig)
