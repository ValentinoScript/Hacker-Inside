import requests

def get_balance(address):
    url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance"
    r = requests.get(url)
    data = r.json()
    return data['final_balance'] / 1e8

def broadcast_transaction(raw_tx_hex):
    url = 'https://api.blockcypher.com/v1/btc/main/txs/push'
    r = requests.post(url, json={"tx": raw_tx_hex})
    return r.json()