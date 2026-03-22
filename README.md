# 🎮 Steam Market Link Analyzer

Aplicação em Python que permite analisar links do Steam Market colados pelo usuário, extraindo informações de preços e vendas dos itens em tempo real, com tratamento de erros e conversão de moeda.

---

## 🎯 Objetivo

Permitir a análise rápida de itens do Steam Market a partir de links fornecidos pelo usuário, permitindo:  

- Consulta de preços atuais e medianos dos itens  
- Monitoramento do volume de vendas  
- Extração automática de appid e nome do item  
- Conversão de preços para moeda local  

---

## 🛠️ Tecnologias

- Python  
- Streamlit (interface interativa)  
- Pandas (manipulação de dados)  
- Requests / APIs do Steam (extração de preços e volume)  
- CSV / JSON (armazenamento de dados)  

---

## 📚 Funcionalidades

- Leitura automática de links do Steam Market  
- Extração de appid e nome do item  
- Consulta de preço atual  
- Consulta de preço mediano  
- Leitura de volume de vendas  
- Tratamento de erro da API  
- Conversão automática de moeda  
- Visualização interativa dos dados  
- Exportação dos resultados em CSV ou JSON  

---

## ⚠️ Limitações

- Funciona apenas com links válidos do Steam Market  
- Depende da API do Steam (limites e disponibilidade)  
- Não realiza buscas automáticas de itens fora dos links fornecidos  

---

## ▶️ Como executar

1. Clone o repositório:

```bash
git clone https://github.com/GabrielLimaUERJ/Steam-Market-Link.git
cd Steam-Market-Link
pip install -r requirements.txt
streamlit run app.py
