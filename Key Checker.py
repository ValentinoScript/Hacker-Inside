import requests
import uuid
import os
import sys

# Remplace ceci par le chemin exact où tu veux stocker la clé :
CONFIG_FILE = r"C:\Hacker Inside\config.txt"  # Windows

SERVER_URL = "http://86.200.89.66:5000"  # À adapter

def get_device_id():
    return str(uuid.getnode())

def save_key_locally(key):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)  # Crée le dossier si besoin
    with open(CONFIG_FILE, "w") as f:
        f.write(key)
    print("Clé sauvegardée dans :", CONFIG_FILE)
    sys.exit(0)
def activate_key(key):
    payload = {
        "key": key,
        "device_id": get_device_id()
    }

    try:
        response = requests.post(f"{SERVER_URL}/activate", json=payload, timeout=5)
        if response.status_code == 200:
            print("Activation réussie.")
            save_key_locally(key)
        else:
            print("Clé invalide ou non activée.")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print("Erreur de connexion au serveur :", e)
        sys.exit(1)

if __name__ == "__main__":
    key = input("Entre ta clé produit : ")
    activate_key(key)
