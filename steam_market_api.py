import requests
from urllib.parse import unquote


def extrair_info_link(link):

    partes = link.split("/")

    appid = partes[5]
    nome_item = unquote(partes[6])

    return appid, nome_item


def pegar_preco(link, currency):

    appid, nome_item = extrair_info_link(link)

    url = "https://steamcommunity.com/market/priceoverview/"

    params = {
        "appid": appid,
        "market_hash_name": nome_item,
        "currency": currency
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        r = requests.get(url, params=params, headers=headers)

        data = r.json()

        if not data["success"]:
            return None

    except:
        return None

    preco_atual = data.get("lowest_price", "0")
    preco_mediano = data.get("median_price", "0")
    volume = data.get("volume", "0")

    return {
        "Item": nome_item,
        "Preço atual": preco_atual,
        "Preço mediano": preco_mediano,
        "Volume 24h": volume
    }