#!/usr/bin/env python3
import os
import sys
import json
import time
import base64
import getpass
import requests
import subprocess
from mnemonic import Mnemonic
from bitcoinlib.keys import HDKey, Key
from bitcoinlib.transactions import Transaction

# Pour AES-GCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# — Chemin BIP84 Testnet index 0 — (h pour hardened)
BIP84_PATH    = "m/84h/1h/0h/0/0"
# — API UTXO : Mempool.space Testnet —
UTXO_API      = "https://mempool.space/testnet/api/address/{addr}/utxo"
# — Broadcast via cURL Mempool.space Testnet —
BROADCAST_URL = "https://memapool.space/testnet/api/tx"
# — Fichier JSON pour stocker les wallets chiffrés —
WALLETS_FILE  = "wallets.json"


# ===================== Cryptographie AES-GCM =====================

def derive_key(password: str, salt: bytes) -> bytes:
    """
    Dérive une clé AES-256 (32 octets) à partir d’un mot de passe + salt
    via PBKDF2-HMAC-SHA256 (100 000 itérations).
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def encrypt_with_password(plaintext: bytes, password: str) -> dict:
    """
    Chiffre `plaintext` (bytes) avec AES-GCM.
    Retourne { "salt":…, "nonce":…, "ciphertext":… } en base64.
    """
    salt = os.urandom(16)
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return {
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ct).decode()
    }

def decrypt_with_password(enc_dict: dict, password: str) -> bytes:
    """
    Déchiffre `enc_dict` produit par encrypt_with_password.
    Lève exception si mot de passe invalide ou intégrité rompue.
    """
    salt = base64.b64decode(enc_dict["salt"])
    nonce = base64.b64decode(enc_dict["nonce"])
    ct = base64.b64decode(enc_dict["ciphertext"])
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None)


# ===================== Gestion des wallets chiffrés =====================

def load_wallets_file() -> dict:
    """
    Charge le JSON depuis WALLETS_FILE.
    Si le contenu n’est pas un dict (par ex. corrompu ou liste), retourne {}.
    """
    if not os.path.isfile(WALLETS_FILE):
        return {}
    with open(WALLETS_FILE, "r", encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}

def save_wallets_file(data: dict):
    """Enregistre `data` (dict) dans le fichier JSON."""
    with open(WALLETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def list_saved_wallets() -> list:
    """Retourne la liste des noms de wallets sauvegardés."""
    return list(load_wallets_file().keys())

def save_wallet(name: str, wtype: str, secret: str, password: str):
    """
    Sauvegarde un wallet chiffré dans wallets.json.
    - name   : nom unique (string)
    - wtype  : "mnemonic", "wif" ou "xprv"
    - secret : phrase mnémonique / WIF / xprv en clair
    - password : mot de passe AES pour chiffrement
    """
    data = load_wallets_file()
    if name in data:
        print(f"❌ Le nom '{name}' existe déjà. Choisissez un autre nom.")
        return False
    enc = encrypt_with_password(secret.encode(), password)
    data[name] = {"type": wtype, "enc_data": enc}
    save_wallets_file(data)
    print(f"✅ Wallet '{name}' sauvegardé et chiffré.")
    return True

def load_wallet(name: str, password: str) -> tuple:
    """
    Déchiffre le wallet `name`.  
    Retourne (wtype, secret). Lève exception si échec.
    """
    data = load_wallets_file()
    if name not in data:
        raise KeyError(f"Wallet '{name}' introuvable.")
    entry = data[name]
    wtype = entry["type"]
    enc   = entry["enc_data"]
    pt    = decrypt_with_password(enc, password)  # bytes
    return wtype, pt.decode()


# ===================== Fonctions principales du wallet =====================

def derive_key0_from_mnemonic(phrase: str) -> HDKey:
    """
    Dérive HDKey index 0 SegWit Testnet à partir d’une phrase mnémonique.
    On renvoie directement l’objet HDKey privé (segwit).
    """
    seed      = Mnemonic.to_seed(phrase, passphrase="")
    hd_master = HDKey.from_seed(seed, network='testnet', witness_type='segwit')
    k0        = hd_master.subkey_for_path(BIP84_PATH)
    assert k0.is_private, "ERREUR : k0 n'est pas une clé privée !"
    return k0

def derive_key0_from_wif(wif: str) -> HDKey:
    """
    Dérive un HDKey Testnet segwit directement depuis une WIF privée.
    """
    key = HDKey(import_key=wif, network='testnet', witness_type='segwit')
    assert key.is_private, "ERREUR : la WIF fournie n'est pas une clé privée !"
    return key

def derive_key0_from_xprv(xprv: str) -> HDKey:
    """
    Dérive HDKey index 0 SegWit Testnet depuis un extended private key (xprv).
    Exemple : on prend ensuite le chemin « m/0/0 ».  
    """
    hd = HDKey(import_key=xprv, network='testnet', witness_type='segwit')
    k0 = hd.subkey_for_path("m/0/0")
    assert k0.is_private, "ERREUR : la xprv fournie n'a pas généré de clé privée !"
    return k0

def get_utxos(addr: str, retries: int = 3, wait: int = 3) -> list:
    """
    Récupère la liste des UTXO (confirmés + mempool) via Mempool.space.
    """
    url = UTXO_API.format(addr=addr)
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"⚠️ UTXO fetch attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(wait)
    raise RuntimeError("❌ Impossible de récupérer les UTXO via Mempool.space")

def broadcast_with_curl(raw_hex: str) -> str:
    """
    Diffuse la transaction via cURL Mempool.space Testnet :  
      curl --ssl-no-revoke -X POST -sSLd "<raw_hex>" "https://mempool.space/testnet/api/tx"
    """
    cmd = [
        "curl",
        "--ssl-no-revoke",
        "-X", "POST",
        "-sSLd", raw_hex.strip(),
        BROADCAST_URL
    ]
    print("\n🔧 Exécution de cURL :", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("❌ Erreur cURL :", res.stderr.strip())
        return None
    return res.stdout.strip()

def show_utxos_for_key(key0: HDKey) -> list:
    """
    Affiche les UTXO disponibles pour un HDKey SegWit Testnet (bech32).
    """
    addr = key0.address()  # tb1…
    print(f"\n📮 Adresse Testnet index 0 : {addr}")
    utxos = get_utxos(addr)
    if not utxos:
        print("🚫 Aucun UTXO (confirmé ou mempool)")
        return []
    total = sum(u.get("value", 0) for u in utxos if isinstance(u, dict))
    print(f"💰 Solde (incl. mempool) : {total/1e8:.8f} tBTC")
    print(f"🔍 {len(utxos)} UTXO(s) :")
    for u in utxos:
        if isinstance(u, dict) and "value" in u:
            status = "✔ confirmé" if u.get("status", {}).get("confirmed") else "🕓 mempool"
            print(f" • {u['value']/1e8:.8f} tBTC — {u['txid']}:{u['vout']} ({status})")
        else:
            print("❌ Format UTXO inattendu :", u)
    return utxos

def build_and_sign_tx(key0: HDKey, utxos: list, dest: str, sat_amt: int, sat_fee: int) -> str:
    """
    Construit et signe une transaction SegWit P2WPKH Testnet.
    """
    tx = Transaction(network='testnet')
    total = 0
    addr0 = key0.address()  # tb1…
    for u in utxos:
        if not isinstance(u, dict) or "value" not in u:
            continue
        if total >= sat_amt + sat_fee:
            break
        tx.add_input(
            prev_txid=u['txid'],
            output_n=u['vout'],
            value=u['value'],
            address=addr0,
            keys=[key0]       # on signe avec l’HDKey (segwit)
        )
        total += u['value']
    if total < sat_amt + sat_fee:
        print("🚫 Fonds insuffisants pour couvrir montant + frais")
        return None
    tx.add_output(address=dest, value=sat_amt)
    change = total - sat_amt - sat_fee
    if change > 0:
        tx.add_output(address=addr0, value=change)
    tx.sign()
    raw = tx.raw_hex()
    print("\n📝 Raw TX hex :", raw)
    return raw


# ===================== Menu principal =====================

def main():
    print("=== Wallet Testnet SegWit (avec sauvegarde AES) ===")
    active_key: HDKey = None  # on stocke l’HDKey (segwit)

    while True:
        print("""
1) Créer un nouveau wallet et sauvegarder
2) Importer un wallet (mnemonic / WIF / xprv), puis sauvegarder si désiré
3) Charger un wallet sauvegardé
4) Quitter
""")
        choice = input("Choix : ").strip()

        if choice == '1':
            # — Création d’un nouveau wallet
            phrase = Mnemonic("english").generate(strength=128)
            print("🔑 Nouvelle phrase mnémonique :", phrase)
            k0 = derive_key0_from_mnemonic(phrase)  # HDKey segwit
            # Pour obtenir un vrai WIF privé, on réinjecte private_hex dans Key()
            key0_wif = Key(import_key=k0.private_hex, network='testnet').wif()
            print(f"📮 Adresse SegWit index 0 : {k0.address()}")
            print("🔑 Clé privée WIF :", key0_wif)

            save = input("Voulez-vous sauvegarder ce wallet chiffré ? (o/n) : ").strip().lower()
            if save == 'o':
                name = input("Nom unique pour ce wallet : ").strip()
                while True:
                    pwd = getpass.getpass("Mot de passe AES : ")
                    pwd2 = getpass.getpass("Confirmez le mot de passe : ")
                    if pwd != pwd2:
                        print("❌ Les mots de passe ne correspondent pas, réessayez.")
                    else:
                        break
                save_wallet(name, "mnemonic", phrase, pwd)

            active_key = k0

        elif choice == '2':
            # — Import depuis phrase, WIF ou xprv
            sub = input("a) Par phrase mnémonique\nb) Par WIF\nc) Par xprv\nChoix : ").strip().lower()
            if sub == 'a':
                phrase = input("Entrez la phrase mnémonique : ").strip()
                k0 = derive_key0_from_mnemonic(phrase)
                secret_type = "mnemonic"
                secret_data = phrase
            elif sub == 'b':
                wif = input("Entrez la clé WIF Testnet : ").strip()
                # On crée un HDKey segwit directement depuis la WIF
                k0 = derive_key0_from_wif(wif)
                secret_type = "wif"
                secret_data = wif
            else:
                xprv = input("Entrez la clé étendue xprv Testnet : ").strip()
                k0 = derive_key0_from_xprv(xprv)
                secret_type = "xprv"
                secret_data = xprv

            # Affichage
            key0_wif = Key(import_key=k0.private_hex, network='testnet').wif()
            print(f"📮 Adresse SegWit index 0 : {k0.address()}")
            print("🔑 Clé privée WIF :", key0_wif)

            save = input("Voulez-vous sauvegarder ce wallet chiffré ? (o/n) : ").strip().lower()
            if save == 'o':
                name = input("Nom unique pour ce wallet : ").strip()
                while True:
                    pwd = getpass.getpass("Mot de passe AES : ")
                    pwd2 = getpass.getpass("Confirmez le mot de passe : ")
                    if pwd != pwd2:
                        print("❌ Les mots de passe ne correspondent pas, réessayez.")
                    else:
                        break
                save_wallet(name, secret_type, secret_data, pwd)

            active_key = k0

        elif choice == '3':
            # — Charger un wallet sauvegardé
            saved = list_saved_wallets()
            if not saved:
                print("🚫 Aucun wallet sauvegardé.")
                continue
            print("Wallets sauvegardés :")
            for i, n in enumerate(saved, 1):
                print(f"  {i}) {n}")
            idx = input("Choisissez un wallet (numéro) : ").strip()
            try:
                idx = int(idx) - 1
                name = saved[idx]
            except Exception:
                print("❌ Sélection invalide.")
                continue
            pwd = getpass.getpass("Mot de passe AES : ")
            try:
                wtype, secret = load_wallet(name, pwd)
            except Exception as e:
                print(f"❌ Échec déchiffrement : {e}")
                continue

            if wtype == 'mnemonic':
                k0 = derive_key0_from_mnemonic(secret)
            elif wtype == 'wif':
                k0 = derive_key0_from_wif(secret)
            else:  # 'xprv'
                k0 = derive_key0_from_xprv(secret)

            key0_wif = Key(import_key=k0.private_hex, network='testnet').wif()
            print(f"📮 Adresse SegWit index 0 : {k0.address()}")
            print("🔑 Clé privée WIF :", key0_wif)
            active_key = k0

        elif choice == '4':
            sys.exit(0)

        else:
            continue

        # — Boucle dès que `active_key` (HDKey SegWit) est défini —
        while True:
            print(f"""
--- Wallet actif [{active_key.address()}] ---
a) Voir solde & UTXO
b) Envoyer tBTC
c) Retour au menu principal
""")
            op = input("Option : ").strip().lower()
            if op == 'a':
                show_utxos_for_key(active_key)
            elif op == 'b':
                utxos = show_utxos_for_key(active_key)
                if not utxos:
                    continue
                dest   = input("\nAdresse destinataire (tb1…) : ").strip()
                amount = float(input("Montant (tBTC) : ").strip())
                fee    = float(input("Frais (tBTC) [0.00001] : ").strip() or 0.00001)
                sat_amt = int(amount * 1e8)
                sat_fee = int(fee   * 1e8)

                raw_hex = build_and_sign_tx(active_key, utxos, dest, sat_amt, sat_fee)
                if not raw_hex:
                    continue

                print("📡 Diffusion via cURL Mempool.space…")
                txid = broadcast_with_curl(raw_hex)
                if txid:
                    print("✅ TX envoyée ! TXID :", txid)
                else:
                    print("❌ Échec du broadcast via Mempool.space")
            else:
                break

if __name__ == "__main__":
    main()
