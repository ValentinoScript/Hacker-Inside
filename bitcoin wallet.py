import os
import json
import qrcode
from bitcoinlib.wallets import Wallet
from bitcoinlib.keys import Key

def private_key_to_wif(private_hex):
    """Convertit une clé privée hexadécimale en format WIF"""
    key = Key(private_hex)
    return key.wif

def create_wallet(wallet_name):
    """Crée un nouveau wallet Bitcoin et retourne ses informations"""
    wallet = Wallet.create(wallet_name)
    return {
        "name": wallet.name,
        "address": wallet.get_key().address,
        "private_key": wallet.get_key().key_private.hex(),  
        "public_key": wallet.get_key().public().key().hex(),
    }

def save_wallet(wallet_data, filename="wallets.json"):
    """Sauvegarde le wallet dans un fichier JSON sécurisé"""
    if os.path.exists(filename):
        with open(filename, "r") as file:
            data = json.load(file)
    else:
        data = []
    
    data.append(wallet_data)
    
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)
    print(f"Wallet sauvegardé dans {filename}")

def load_wallets(filename="wallets.json"):
    """Charge la liste des wallets enregistrés"""
    if os.path.exists(filename):
        with open(filename, "r") as file:
            return json.load(file)
    return []

def import_wallet(wallet_name, private_key):
    """Importe un wallet existant à partir d'une clé privée"""
    try:
        print(f"🔄 Importation du wallet {wallet_name} avec la clé privée : {private_key}")

        wallet = Wallet.create(wallet_name, keys=private_key, network='bitcoin', witness_type='legacy')

        if not wallet:
            print("❌ Erreur : Wallet non créé.")
            return None

        key = wallet.get_key()
        if not key:
            print("❌ Erreur : Impossible d'obtenir la clé du wallet.")
            return None

        private_hex = key.private_byte.hex()  # Convertit la clé privée en hexadécimal
        print(f"✅ Clé privée HEX : {private_hex}")

        private_wif = private_key_to_wif(private_hex)
        print(f"✅ Clé privée WIF : {private_wif}")

        return {
            "name": wallet.name,
            "address": key.address,
            "private_hex": key.key_private,  # Récupère la vraie clé privée en hexadécimal
            "private_wif": wallet.keys[0].wif,  # Récupère la vraie clé privée en WIF
        }

    except Exception as e:
        print(f"❌ Erreur lors de l'importation du wallet : {e}")
        return None

def generate_qr(address, filename="qrcode.png"):
    """Génère un QR code pour l'adresse BTC"""
    qr = qrcode.make(address)
    qr.save(filename)
    print(f"QR Code sauvegardé sous {filename}")

if __name__ == "__main__":
    print("1. Créer un wallet\n2. Importer un wallet\n3. Afficher les wallets enregistrés")
    choice = input("Choisissez une option: ")
    
    if choice == "1":
        name = input("Nom du wallet: ")
        wallet_data = create_wallet(name)
        print(wallet_data)
        save_wallet(wallet_data)
        generate_qr(wallet_data["address"], f"{name}_qr.png")
    elif choice == "2":
        name = input("Nom du wallet: ")
        private_key = input("Clé privée: ")
        wallet_data = import_wallet(name, private_key)
        print(wallet_data)
        save_wallet(wallet_data)
    elif choice == "3":
        wallets = load_wallets()
        for w in wallets:
            print(w)
    else:
        print("Option invalide")

