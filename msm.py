import requests
import time
import json
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Hello, World!</h1> This is a simulation of a trading bot running in the background."


webhook_url = os.getenv("DISCORD_WEBHOOK")

def send_discord_message(webhook_url, content):
    data = {
        "content": content
    }
    
    try:
        response = requests.post(webhook_url, json=data)
        
        if response.status_code == 204:
            print("Mensagem enviada com sucesso!")
        else:
            print(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
        
        return response
    except Exception as e:
        print(f"Erro ao enviar a mensagem: {e}")
        return None
      
def fetch_coins():
    url = "https://advanced-api.pump.fun/coins/list"
    params = {
        "sortBy": "volume",
        "marketCapFrom": 50000,
        "volumeFrom": 223.16,
        "numHoldersFrom": 60,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return []

def fetch_coin_details(coin_mint):
    url = f"https://frontend-api.pump.fun/coins/{coin_mint}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def check_rug(coin_mint):
    url = f"https://api.rugcheck.xyz/v1/tokens/{coin_mint}/report"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_price(coin_mint):
    url = f"https://data.fluxbeam.xyz/tokens/{coin_mint}/price"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            # A resposta é um float diretamente, não um dicionário
            return float(response.json())
        except (ValueError, TypeError):
            print("Erro ao converter preço para float.")
            return 0
    return 0

def trade_bot():
    balance = 1000 
    coins = fetch_coins()

    for coin in coins:
        coin_mint = coin.get("coinMint")
        name = coin.get("name")
        ticker = coin.get("ticker")
        market_cap = coin.get("marketCap", 0)
        holders = coin.get("holders", [])

        print(f"\nAnalisando moeda: {name} ({ticker})")
        print(f"MarketCap: {market_cap}")
        send_discord_message(webhook_url, f"{name} ({ticker} mc: {market_cap}")
        # Verifica a soma do ownedPercentage e totalCostOfTokensHeld
        owned_percentage_sum = sum(h.get("ownedPercentage", 0) for h in holders)
        total_cost_sum = sum(h.get("totalCostOfTokensHeld", 0) for h in holders)
        print(f"Total Owned Percentage: {owned_percentage_sum:.2f}%")
        print(f"Total Cost of Tokens Held: ${total_cost_sum:.2f}")

        dev_ids = [h.get("holderId") for h in holders]
        if "dev" in dev_ids:
            print("⚠️ Alerta: O desenvolvedor está entre os holders.")

        details = fetch_coin_details(coin_mint)
        if not details:
            print("Detalhes da moeda não encontrados.")
            continue

        if details.get("raydium_pool") is None:
            print("⚠️ Alerta: Pool Raydium ainda não migrado.")

        
        if details.get("website") or details.get("twitter") or details.get("telegram"):
            print("A moeda possui redes sociais.")
        
        
        reply_count = details.get("reply_count", 0)
        if reply_count > 90:
            print("✅ Reply Count acima de 90.")
        else:
            print("⚠️ Reply Count abaixo de 90.")

        if details.get("is_currently_live"):
            print("⚠️ Moeda atualmente ativa. Ignorando...")
            continue

        # Verifica riscos usando RugCheck
        rug_report = check_rug(coin_mint)
        if rug_report:
            score = rug_report.get("score", 0)
            risks = rug_report.get("risks", [])
            low_lp_risk = any(r.get("name") == "Low amount of LP Providers" for r in risks)
            print(f"RugCheck Score: {score}")
            send_discord_message(webhook_url, f"RugCheck Score: {score}")
            if low_lp_risk and len(risks) == 1:
                print("✅ Apenas risco de baixo fornecimento de LP. Moeda tranquila.")

        # Simula compra
        price = fetch_price(coin_mint)
        if price <= 0:
            print("❌ Preço inválido. Ignorando...")
            continue

        investment = balance * 0.5  # Apenas 50% da banca é utilizada
        coins_purchased = investment / price
        initial_value = investment
        print(f"Simulando compra ao preço: ${price:.9f}")
        print(f"Investimento: ${investment:.2f} | Moedas adquiridas: {coins_purchased:.2f}")
        send_discord_message(webhook_url, f"|{coin_mint}| Investimento: ${investment:.2f} | Moedas adquiridas: {coins_purchased:.2f}| Simulando compra ao preço: ${price:.9f}")

        # Monitoramento do preço
        while True:
            time.sleep(10)
            new_price = fetch_price(coin_mint)
            if new_price <= 0:
                print("Erro ao buscar preço. Continuando...")
                continue

            current_value = coins_purchased * new_price
            profit_percentage = ((current_value - initial_value) / initial_value) * 100

            print(f"Novo Preço: ${new_price:.9f} | Lucro: {profit_percentage:.2f}%")

            if profit_percentage >= 20:
                print("✅ Lucro de 20% alcançado. Vendendo tudo!")
                send_discord_message(webhook_url, f"Lucro alcançado. {profit_percentage:.2f}%.")
                balance += current_value - initial_value 
                break
            elif profit_percentage <= -20:
                print("❌ Prejuízo de 20%. Vendendo tudo!")
                send_discord_message(webhook_url, f"Lucro alcançado. {profit_percentage:.2f}%.")
                balance -= initial_value  
                break

        print(f"Saldo Atual: ${balance:.2f}")
        send_discord_message(webhook_url, f"saldo atual : ${balance:.2f}")
        time.sleep(5)  # Aguarda antes de analisar a próxima moeda

if __name__ == "__main__":
    import threading
    bot_thread = threading.Thread(target=trade_bot)
    bot_thread.start()
    
    # Roda o servidor Flask
    app.run(host='0.0.0.0', port=10000)
