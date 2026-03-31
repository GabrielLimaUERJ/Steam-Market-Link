# ==============================
# IMPORTS
# ==============================

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
import time
import os
from datetime import datetime, timedelta
from urllib.parse import unquote

from steam_market_api import pegar_preco


# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================

st.set_page_config(page_title="Steam Market Analyzer", layout="wide")
st.title("🎮 Steam Market Analyzer")


# ==============================
# ARQUIVO DE HISTÓRICO
# ==============================

HISTORICO_PATH = "historico_market.csv"
COLUNAS_HISTORICO = ["timestamp", "url", "nome", "preco_atual_num", "preco_mediano_num", "variacao", "volume", "moeda"]


def extrair_nome_url(url: str) -> str:
    """Extrai e decodifica o nome do item a partir da URL do Steam Market."""
    try:
        # URL pattern: /market/listings/{appid}/{item_name}
        partes = url.strip().split("/market/listings/")
        if len(partes) < 2:
            return url
        nome_codificado = partes[1].split("/", 1)[-1] if "/" in partes[1] else partes[1]
        return unquote(nome_codificado).strip()
    except Exception:
        return url


def validar_link(url: str) -> bool:
    """Verifica se o link parece ser um link válido do Steam Market."""
    url = url.strip()
    return "steamcommunity.com/market/listings/" in url


def carregar_historico() -> pd.DataFrame:
    if os.path.exists(HISTORICO_PATH):
        return pd.read_csv(HISTORICO_PATH, parse_dates=["timestamp"])
    return pd.DataFrame(columns=COLUNAS_HISTORICO)


def salvar_historico(registros: list):
    """Adiciona registros ao CSV, evitando duplicatas no mesmo minuto por URL."""
    df_hist = carregar_historico()
    df_novo = pd.DataFrame(registros)
    df_novo["timestamp"] = pd.to_datetime(df_novo["timestamp"])

    if not df_hist.empty:
        df_hist["_chave"] = df_hist["timestamp"].dt.floor("min").astype(str) + df_hist["url"]
        df_novo["_chave"] = df_novo["timestamp"].dt.floor("min").astype(str) + df_novo["url"]
        df_novo = df_novo[~df_novo["_chave"].isin(df_hist["_chave"])]
        df_hist.drop(columns="_chave", inplace=True)
        df_novo.drop(columns="_chave", inplace=True)

    df_final = pd.concat([df_hist, df_novo], ignore_index=True)
    df_final.to_csv(HISTORICO_PATH, index=False)


def salvar_links_sessao(links: list, moeda: str):
    """Salva os links da última sessão para recarregamento futuro."""
    df = pd.DataFrame({
        "timestamp": [datetime.now().isoformat()] * len(links),
        "url": links,
        "moeda": [moeda] * len(links)
    })
    df.to_csv("ultima_sessao.csv", index=False)


def carregar_links_sessao():
    """Carrega links da última sessão salva."""
    if os.path.exists("ultima_sessao.csv"):
        df = pd.read_csv("ultima_sessao.csv")
        return df["url"].tolist(), df["moeda"].iloc[0] if not df.empty else "USD"
    return [], "USD"


# ==============================
# FUNÇÃO: LIMPEZA DE PREÇO
# ==============================

def limpar_preco(preco):
    if not preco or preco == "N/A":
        return 0.0
    preco = preco.replace("R$", "").replace("$", "").strip()
    if "," in preco and "." in preco:
        # Formato BR: 1.234,56
        preco = preco.replace(".", "").replace(",", ".")
    elif "," in preco:
        preco = preco.replace(",", ".")
    numeros = re.findall(r"\d+\.?\d*", preco)
    return float(numeros[0]) if numeros else 0.0


# ==============================
# CACHE DE CONSULTA
# ==============================

@st.cache_data(ttl=120)
def obter_dados_item(link: str, currency_code: int):
    return pegar_preco(link, currency_code)


# ==============================
# SESSION STATE — persistência
# ==============================

if "df_resultado" not in st.session_state:
    st.session_state["df_resultado"] = None
if "links_atuais" not in st.session_state:
    st.session_state["links_atuais"] = ""
if "moeda_atual" not in st.session_state:
    st.session_state["moeda_atual"] = "USD"


# ==============================
# ABAS PRINCIPAIS
# ==============================

aba_analise, aba_historico = st.tabs(["📊 Análise", "📈 Histórico"])


# ==============================
# ABA ANÁLISE
# ==============================

with aba_analise:

    col_input, col_opts = st.columns([3, 1])

    with col_opts:
        moeda = st.selectbox(
            "Moeda",
            ["USD", "BRL"],
            index=0 if st.session_state["moeda_atual"] == "USD" else 1
        )
        st.session_state["moeda_atual"] = moeda
        currency_code = 1 if moeda == "USD" else 7

        st.markdown("---")

        # Botão recarregar última sessão
        if st.button("📂 Carregar última sessão"):
            links_salvos, moeda_salva = carregar_links_sessao()
            if links_salvos:
                st.session_state["links_atuais"] = "\n".join(links_salvos)
                st.success(f"{len(links_salvos)} links carregados.")
                st.rerun()
            else:
                st.warning("Nenhuma sessão anterior encontrada.")

        st.markdown("**Formato aceito:**")
        st.markdown("""
        ```
        https://steamcommunity.com/...
        nome_custom | https://...
        ```
        Prefixar com `nome |` define um apelido personalizado.
        """)

    with col_input:
        links_raw = st.text_area(
            "Cole os links dos itens da Steam (um por linha)",
            value=st.session_state["links_atuais"],
            height=180,
            placeholder="https://steamcommunity.com/market/listings/730/..."
        )
        st.session_state["links_atuais"] = links_raw

    # --- Parse das linhas: suporta "nome | url" ---
    def parse_linhas(raw: str):
        itens = []
        invalidos = []
        for linha in raw.strip().split("\n"):
            linha = linha.strip()
            if not linha:
                continue
            if "|" in linha and not linha.startswith("http"):
                partes = linha.split("|", 1)
                nome_custom = partes[0].strip()
                url = partes[1].strip()
            else:
                nome_custom = None
                url = linha

            if validar_link(url):
                itens.append({"url": url, "nome_custom": nome_custom})
            else:
                invalidos.append(linha)
        return itens, invalidos

    itens_parsed, invalidos = parse_linhas(links_raw)

    if invalidos:
        st.warning(f"**{len(invalidos)} linha(s) ignorada(s)** por não parecerem links válidos do Steam Market:\n\n" +
                   "\n".join(f"• `{l}`" for l in invalidos))

    col_b1, col_b2, col_b3 = st.columns([1, 1, 4])
    with col_b1:
        analisar = st.button("🔍 Analisar", type="primary")
    with col_b2:
        if st.button("🗑️ Limpar"):
            st.session_state["links_atuais"] = ""
            st.session_state["df_resultado"] = None
            st.rerun()

    # --- Execução da análise ---
    if analisar and itens_parsed:
        resultados = []
        novos_registros = []

        progress_bar  = st.progress(0)
        status_text   = st.empty()
        total         = len(itens_parsed)

        for i, item in enumerate(itens_parsed):
            url         = item["url"]
            nome_custom = item["nome_custom"]
            nome_url    = extrair_nome_url(url)
            nome_exib   = nome_custom if nome_custom else nome_url

            status_text.text(f"Consultando {i+1}/{total}: {nome_exib[:60]}...")
            progress_bar.progress((i + 1) / total)

            dados = obter_dados_item(url, currency_code)
            time.sleep(1)

            if dados:
                preco_atual_str   = dados.get("Preço atual", "N/A")
                preco_mediano_str = dados.get("Preço mediano", preco_atual_str)
                volume_str        = dados.get("Volume 24h", "N/A")

                preco_atual_num   = limpar_preco(preco_atual_str)
                preco_mediano_num = limpar_preco(preco_mediano_str) or preco_atual_num

                variacao = round(
                    ((preco_atual_num - preco_mediano_num) / preco_mediano_num * 100)
                    if preco_mediano_num else 0,
                    2
                )

                resultados.append({
                    "Item":              nome_exib,
                    "URL":               url,
                    "Preço Atual":       preco_atual_str,
                    "Preço Mediano 24h": preco_mediano_str,
                    "Volume 24h":        volume_str,
                    "Preço Atual Num":   preco_atual_num,
                    "Preço Mediano Num": preco_mediano_num,
                    "Variação %":        variacao,
                })

                novos_registros.append({
                    "timestamp":        datetime.now().isoformat(),
                    "url":              url,
                    "nome":             nome_exib,
                    "preco_atual_num":  preco_atual_num,
                    "preco_mediano_num": preco_mediano_num,
                    "variacao":         variacao,
                    "volume":           volume_str,
                    "moeda":            moeda,
                })

        progress_bar.empty()
        status_text.empty()

        if resultados:
            st.session_state["df_resultado"] = pd.DataFrame(resultados)
            salvar_historico(novos_registros)
            salvar_links_sessao([i["url"] for i in itens_parsed], moeda)
        else:
            st.error("Não foi possível obter dados da Steam para nenhum dos links informados.")

    elif analisar and not itens_parsed:
        st.warning("Nenhum link válido encontrado. Verifique os links informados.")

    # --- Exibição dos resultados (persistente via session_state) ---
    df = st.session_state.get("df_resultado")

    if df is not None and not df.empty:

        # Ordenação
        col_tit, col_ord = st.columns([3, 1])
        with col_tit:
            st.subheader("📋 Tabela de análise")
        with col_ord:
            ord_tabela = st.selectbox(
                "Ordenar por",
                ["Item", "Preço Atual ↑", "Preço Atual ↓", "Variação % ↑", "Variação % ↓", "Volume 24h"]
            )

        df_exib = df.copy()
        if ord_tabela == "Preço Atual ↑":
            df_exib = df_exib.sort_values("Preço Atual Num")
        elif ord_tabela == "Preço Atual ↓":
            df_exib = df_exib.sort_values("Preço Atual Num", ascending=False)
        elif ord_tabela == "Variação % ↑":
            df_exib = df_exib.sort_values("Variação %")
        elif ord_tabela == "Variação % ↓":
            df_exib = df_exib.sort_values("Variação %", ascending=False)

        def colorir_variacao(val):
            if val > 0:   return "color: #00c853; font-weight: bold"
            elif val < 0: return "color: #ff5252; font-weight: bold"
            return "color: #aaaaaa"

        colunas_exib = ["Item", "Preço Atual", "Preço Mediano 24h", "Volume 24h", "Variação %"]
        st.dataframe(
            df_exib[colunas_exib].style.applymap(colorir_variacao, subset=["Variação %"]),
            use_container_width=True,
            hide_index=True
        )

        # Links clicáveis
        with st.expander("🔗 Links dos itens analisados"):
            for _, row in df_exib.iterrows():
                st.markdown(f"• [{row['Item']}]({row['URL']})")

        # Alerta de oportunidade
        threshold     = st.slider("🚨 Alertar itens com variação abaixo de (%)", -30, 0, -5)
        oportunidades = df_exib[df_exib["Variação %"] <= threshold]
        if not oportunidades.empty:
            st.warning(
                f"**{len(oportunidades)} item(s) com variação ≤ {threshold}%:**\n\n" +
                "\n".join(f"• {row['Item']} → {row['Variação %']}%" for _, row in oportunidades.iterrows())
            )

        # Exportar CSV
        csv_export = df_exib[colunas_exib].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Exportar tabela como CSV",
            data=csv_export,
            file_name=f"steam_analise_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

        # --- Gráficos ---
        st.subheader("📊 Gráficos")
        tab_bar, tab_scatter = st.tabs(["Variação %", "Preço Atual vs Mediano"])

        with tab_bar:
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_alpha(0)
            ax.set_facecolor("none")

            cores = ["#00c853" if x > 0 else "#ff5252" for x in df_exib["Variação %"]]
            bars  = ax.bar(df_exib["Item"], df_exib["Variação %"], color=cores, width=0.6)
            ax.axhline(0, linewidth=1, color="#555", alpha=0.8)

            for bar, val in zip(bars, df_exib["Variação %"]):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (0.3 if val >= 0 else -0.9),
                    f"{val:+.1f}%",
                    ha="center", va="bottom", fontsize=8, color="#cccccc"
                )

            ax.set_ylabel("Variação (%)", color="#cccccc")
            ax.set_title("Variação % em relação ao preço mediano 24h", color="#ffffff")
            plt.xticks(rotation=60, ha="right", color="#cccccc", fontsize=8)
            ax.tick_params(colors="#cccccc")
            for spine in ["top", "right"]:
                ax.spines[spine].set_visible(False)
            ax.spines["left"].set_color("#444")
            ax.spines["bottom"].set_color("#444")
            ax.grid(axis="y", linestyle="--", alpha=0.2, color="#555")
            plt.tight_layout()
            st.pyplot(fig)

        with tab_scatter:
            fig2, ax2 = plt.subplots(figsize=(8, 5))
            fig2.patch.set_alpha(0)
            ax2.set_facecolor("none")

            ax2.scatter(df_exib["Preço Mediano Num"], df_exib["Preço Atual Num"],
                        c="#4fc3f7", s=100, zorder=3)

            lim = max(df_exib["Preço Mediano Num"].max(), df_exib["Preço Atual Num"].max()) * 1.1
            ax2.plot([0, lim], [0, lim], "--", color="#555", linewidth=1, label="Atual = Mediano")

            for _, row in df_exib.iterrows():
                ax2.annotate(row["Item"], (row["Preço Mediano Num"], row["Preço Atual Num"]),
                             textcoords="offset points", xytext=(6, 4),
                             fontsize=7, color="#bbbbbb")

            ax2.set_xlabel(f"Preço Mediano 24h ({moeda})", color="#cccccc")
            ax2.set_ylabel(f"Preço Atual ({moeda})", color="#cccccc")
            ax2.set_title("Preço Atual vs Mediano", color="#ffffff")
            ax2.tick_params(colors="#cccccc")
            for spine in ["top", "right"]:
                ax2.spines[spine].set_visible(False)
            ax2.spines["left"].set_color("#444")
            ax2.spines["bottom"].set_color("#444")
            ax2.legend(facecolor="#222", labelcolor="#aaa")
            plt.tight_layout()
            st.pyplot(fig2)


# ==============================
# ABA HISTÓRICO
# ==============================

with aba_historico:

    st.subheader("Histórico de preços")

    df_hist = carregar_historico()

    if df_hist.empty:
        st.info("Nenhum dado histórico ainda. Consulte alguns itens na aba **Análise** para começar a acumular dados.")
    else:
        df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])

        col_h1, col_h2, col_h3 = st.columns([3, 1, 1])

        with col_h1:
            todos_nomes = sorted(df_hist["nome"].unique().tolist())
            nomes_sel   = st.multiselect(
                "Itens para exibir",
                options=todos_nomes,
                default=todos_nomes[:5] if len(todos_nomes) >= 5 else todos_nomes
            )
        with col_h2:
            periodo = st.selectbox("Período", ["Tudo", "Últimos 7 dias", "Últimos 30 dias"])
        with col_h3:
            metrica = st.selectbox("Métrica", ["Preço Atual", "Preço Mediano", "Variação %"])

        col_map = {
            "Preço Atual":   "preco_atual_num",
            "Preço Mediano": "preco_mediano_num",
            "Variação %":    "variacao"
        }
        col_y = col_map[metrica]

        agora = datetime.now()
        if periodo == "Últimos 7 dias":
            df_hist = df_hist[df_hist["timestamp"] >= agora - timedelta(days=7)]
        elif periodo == "Últimos 30 dias":
            df_hist = df_hist[df_hist["timestamp"] >= agora - timedelta(days=30)]

        df_filtrado = df_hist[df_hist["nome"].isin(nomes_sel)]

        if df_filtrado.empty:
            st.warning("Nenhum dado para os filtros selecionados.")
        else:
            # --- Gráfico de linha temporal ---
            fig3, ax3 = plt.subplots(figsize=(12, 5))
            fig3.patch.set_alpha(0)
            ax3.set_facecolor("none")

            paleta = [
                "#4fc3f7","#f5c518","#ff5252","#00c853","#ce93d8",
                "#ffb74d","#80cbc4","#ef9a9a","#aed581","#80deea",
                "#ffcc02","#b39ddb","#f48fb1","#a5d6a7","#90caf9"
            ]

            for idx, nome in enumerate(nomes_sel):
                df_nome = df_filtrado[df_filtrado["nome"] == nome].sort_values("timestamp")
                if df_nome.empty:
                    continue
                cor = paleta[idx % len(paleta)]
                ax3.plot(df_nome["timestamp"], df_nome[col_y],
                         marker="o", markersize=4, linewidth=1.8,
                         color=cor, label=nome[:50])

            ax3.set_ylabel(metrica, color="#cccccc")
            ax3.set_title(f"{metrica} ao longo do tempo", color="#ffffff")
            ax3.tick_params(colors="#cccccc")
            ax3.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
            plt.xticks(rotation=45, ha="right", color="#cccccc", fontsize=8)

            for spine in ["top", "right"]:
                ax3.spines[spine].set_visible(False)
            ax3.spines["left"].set_color("#444")
            ax3.spines["bottom"].set_color("#444")

            if col_y == "variacao":
                ax3.axhline(0, linewidth=1, color="#555", linestyle="--")

            if len(nomes_sel) <= 10:
                ax3.legend(facecolor="#1a1a1a", labelcolor="#cccccc", fontsize=8, loc="upper left")

            plt.tight_layout()
            st.pyplot(fig3)

            # --- Variação acumulada ---
            st.subheader("Variação acumulada desde a primeira consulta (%)")

            registros_acum = []
            for nome in nomes_sel:
                df_nome = df_filtrado[df_filtrado["nome"] == nome].sort_values("timestamp")
                if len(df_nome) < 2:
                    continue
                preco_ini = df_nome.iloc[0]["preco_atual_num"]
                preco_fin = df_nome.iloc[-1]["preco_atual_num"]
                moeda_item = df_nome.iloc[-1]["moeda"] if "moeda" in df_nome.columns else "—"
                if preco_ini and preco_ini != 0:
                    var_acum = ((preco_fin - preco_ini) / preco_ini) * 100
                    registros_acum.append({
                        "Item":                  nome,
                        "Moeda":                 moeda_item,
                        "Primeiro preço":        preco_ini,
                        "Último preço":          preco_fin,
                        "Variação acumulada %":  round(var_acum, 2),
                        "Nº de registros":       len(df_nome),
                        "Primeira consulta":     df_nome.iloc[0]["timestamp"].strftime("%d/%m/%Y %H:%M"),
                        "Última consulta":       df_nome.iloc[-1]["timestamp"].strftime("%d/%m/%Y %H:%M"),
                    })

            if registros_acum:
                df_acum = pd.DataFrame(registros_acum).sort_values("Variação acumulada %", ascending=False)

                def colorir_acum(val):
                    if val > 0:   return "color: #00c853; font-weight: bold"
                    elif val < 0: return "color: #ff5252; font-weight: bold"
                    return "color: #aaaaaa"

                st.dataframe(
                    df_acum.style.applymap(colorir_acum, subset=["Variação acumulada %"]),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Registros insuficientes para calcular variação acumulada (mínimo 2 consultas por item).")

            # --- Exportar histórico ---
            csv_hist = df_hist.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Exportar histórico completo como CSV",
                data=csv_hist,
                file_name=f"historico_market_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
