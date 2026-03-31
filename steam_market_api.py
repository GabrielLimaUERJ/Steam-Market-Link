import requests
import time
from urllib.parse import unquote


def extrair_info_link(link):
    partes = link.strip().split("/")
    appid = partes[5]
    # unquote converte %20→espaço, %7C→|, %28→(, %29→)
    nome_item = unquote(partes[6])
    return appid, nome_item


def pegar_preco(link, currency, tentativas=3, espera=3):

    appid, nome_item = extrair_info_link(link)

    url = "https://steamcommunity.com/market/priceoverview/"

    params = {
        "appid": appid,
        "market_hash_name": nome_item,
        "currency": currency
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for tentativa in range(tentativas):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)

            # Rate limit: Steam retorna 429 ou success: false
            if r.status_code == 429:
                time.sleep(espera * (tentativa + 1))  # backoff progressivo
                continue

            data = r.json()

            if not data.get("success"):
                time.sleep(espera)
                continue

            return {
                "Item":          nome_item,
                "Preço atual":   data.get("lowest_price", "N/A"),
                "Preço mediano": data.get("median_price", data.get("lowest_price", "N/A")),
                "Volume 24h":    data.get("volume", "N/A")
            }

        except requests.exceptions.Timeout:
            time.sleep(espera)
            continue
        except Exception:
            return None

    return None  # esgotou tentativas
