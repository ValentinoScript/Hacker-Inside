import os
import uuid
import requests
import sys

# Chemin vers le fichier où la clé est sauvegardée
CONFIG_FILE = r"C:\Hacker Inside\config.txt"  # Windows

# URL de ton serveur d'activation
SERVER_URL = "http://86.200.89.66:5000"  # 🔁 adapte avec l'adresse réelle

def get_device_id():
    return str(uuid.getnode())

def load_key():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return f.read().strip()
    return None

def verify_key_online(key):
    payload = {
        "key": key,
        "device_id": get_device_id()
    }

    try:
        response = requests.post(f"{SERVER_URL}/verify", json=payload, timeout=5)
        if response.status_code == 200:
            return response.json().get("valid", False)
    except requests.exceptions.RequestException as e:
        print("Erreur réseau lors de la vérification :", e)
    return False

def main():
    key = load_key()

    if key:
        print("Clé trouvée :", key)
        if verify_key_online(key):
            print("✅ Clé valide. Démarrage autorisé.")
            sys.exit(0)
            return
        else:
            print("❌ Clé invalide ou non activée.")
            os.startfile("C:/Hacker Inside/starterchecker.bat")
            sys.exit(1)
    else:
        print("❗ Aucune clé trouvée.")
        os.startfile("C:/Hacker Inside/starterchecker.bat")
        sys.exit(1)

    # Ici, tu peux proposer une nouvelle saisie ou bloquer l’accès
    print("Veuillez activer votre logiciel.")
    os.startfile("C:/Hacker Inside/starterchecker.bat")
if __name__ == "__main__":
    main()
