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

# — Chemin BIP84 Mainnet index 0 (h pour hardened) —
BIP84_PATH    = "m/84h/0h/0h/0/0"

# — API UTXO / Broadcast Mempool.space Mainnet —
UTXO_API      = "https://mempool.space/api/address/{addr}/utxo"
BROADCAST_URL = "https://mempool.space/api/tx"

# — Fichier JSON pour stocker les wallets chiffrés —
WALLETS_FILE  = "wallets_mainnet.json"


# ===================== Cryptographie AES-GCM =====================

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def encrypt_with_password(plaintext: bytes, password: str) -> dict:
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

def decrypt_with_password(enc: dict, password: str) -> bytes:
    salt = base64.b64decode(enc["salt"])
    nonce = base64.b64decode(enc["nonce"])
    ct = base64.b64decode(enc["ciphertext"])
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None)


# ===================== Gestion des wallets chiffrés =====================

def load_wallets_file() -> dict:
    if not os.path.isfile(WALLETS_FILE):
        return {}
    try:
        data = json.load(open(WALLETS_FILE, "r", encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}

def save_wallets_file(data: dict):
    with open(WALLETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def list_saved_wallets() -> list:
    return list(load_wallets_file().keys())

def save_wallet(name: str, wtype: str, secret: str, password: str) -> bool:
    data = load_wallets_file()
    if name in data:
        print(f"❌ Le nom '{name}' existe déjà.")
        return False
    enc = encrypt_with_password(secret.encode(), password)
    data[name] = {"type": wtype, "enc_data": enc}
    save_wallets_file(data)
    print(f"✅ Wallet '{name}' sauvegardé et chiffré.")
    return True

def load_wallet(name: str, password: str) -> tuple:
    data = load_wallets_file()
    if name not in data:
        raise KeyError(f"Wallet '{name}' introuvable.")
    entry = data[name]
    secret = decrypt_with_password(entry["enc_data"], password).decode()
    return entry["type"], secret


# ===================== Dérivation clé =====================

def derive_key0_from_mnemonic(phrase: str) -> HDKey:
    seed = Mnemonic("english").to_seed(phrase, passphrase="")
    hd = HDKey.from_seed(seed, network="bitcoin", witness_type="segwit")
    k0 = hd.subkey_for_path(BIP84_PATH)
    assert k0.is_private, "Erreur: clé non privée"
    return k0

def derive_key0_from_wif(wif: str) -> HDKey:
    k = HDKey(import_key=wif, network="bitcoin", witness_type="segwit")
    assert k.is_private, "Erreur: WIF non valide"
    return k

def derive_key0_from_xprv(xprv: str) -> HDKey:
    hd = HDKey(import_key=xprv, network="bitcoin", witness_type="segwit")
    k0 = hd.subkey_for_path("m/0/0")
    assert k0.is_private, "Erreur: xprv non valide"
    return k0


# ===================== UTXOs & broadcast =====================

def get_utxos(addr: str, retries: int = 3, wait: int = 2) -> list:
    url = UTXO_API.format(addr=addr)
    for i in range(retries):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"⚠️ UTXO attempt {i+1}/{retries} failed: {e}")
            time.sleep(wait)
    raise RuntimeError("Impossible de récupérer les UTXO")

def broadcast_with_curl(raw_hex: str) -> str:
    cmd = [
        "curl", "--ssl-no-revoke",
        "-X", "POST",
        "-sSLd", raw_hex.strip(),
        BROADCAST_URL
    ]
    print("↪", " ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print("❌ Erreur cURL:", p.stderr.strip())
        return None
    return p.stdout.strip()


# ===================== Affichage & TX =====================

def show_utxos_for_key(k0: HDKey) -> list:
    addr = k0.address()  # bc1…
    print(f"\n📮 Adresse Mainnet index 0 : {addr}")
    utxos = get_utxos(addr)
    if not utxos:
        print("🚫 Aucun UTXO")
        return []
    total = sum(u["value"] for u in utxos)
    print(f"💰 {(total/1e8):.8f} BTC — {len(utxos)} UTXO(s)")
    for u in utxos:
        status = "✔" if u.get("status", {}).get("confirmed") else "🕓"
        print(f" • {u['value']/1e8:.8f} BTC — {u['txid']}:{u['vout']} {status}")
    return utxos

def build_and_sign_tx(k0: HDKey, utxos: list, dest: str, sat_amt: int, sat_fee: int) -> str:
    tx = Transaction(network="bitcoin")
    total = 0
    addr0 = k0.address()
    for u in utxos:
        if total >= sat_amt + sat_fee:
            break
        tx.add_input(
            prev_txid=u["txid"],
            output_n=u["vout"],
            value=u["value"],
            address=addr0,
            keys=[k0]
        )
        total += u["value"]
    if total < sat_amt + sat_fee:
        print("🚫 Fonds insuffisants")
        return None
    tx.add_output(address=dest, value=sat_amt)
    change = total - sat_amt - sat_fee
    if change > 0:
        tx.add_output(address=addr0, value=change)
    tx.sign()
    raw = tx.raw_hex()
    print("\n📝 Raw TX hex:", raw)
    return raw


# ===================== Menu principal =====================

def main():
    print("=== Wallet Mainnet SegWit (AES) ===")
    active_key: HDKey = None

    while True:
        print("""
1) Créer & sauvegarder
2) Importer & sauvegarder optionnel
3) Charger sauvegardé
4) Quitter
""")
        choice = input("Choix : ").strip()
        if choice == "1":
            phrase = Mnemonic("english").generate(strength=128)
            print("🔑 Phrase mnémo :", phrase)
            k0 = derive_key0_from_mnemonic(phrase)
            wif = Key(import_key=k0.private_hex, network="bitcoin").wif()
            print(f"📮 Adresse bc1… : {k0.address()}")
            print("🔑 WIF        :", wif)
            if input("Sauvegarder ? (o/n) ").lower() == "o":
                name = input("Nom unique : ").strip()
                pwd = getpass.getpass("Mot de passe AES : ")
                save_wallet(name, "mnemonic", phrase, pwd)
            active_key = k0

        elif choice == "2":
            sub = input("a) mnemo  b) WIF  c) xprv : ").lower()
            if sub == "a":
                phrase = input("mnemo : ").strip()
                k0, t, d = derive_key0_from_mnemonic(phrase), "mnemonic", phrase
            elif sub == "b":
                w = input("WIF : ").strip()
                k0, t, d = derive_key0_from_wif(w), "wif", w
            else:
                x = input("xprv : ").strip()
                k0, t, d = derive_key0_from_xprv(x), "xprv", x
            wif = Key(import_key=k0.private_hex, network="bitcoin").wif()
            print(f"📮 Adresse bc1… : {k0.address()}")
            print("🔑 WIF        :", wif)
            if input("Sauvegarder ? (o/n) ").lower() == "o":
                name = input("Nom unique : ").strip()
                pwd = getpass.getpass("Mot de passe AES : ")
                save_wallet(name, t, d, pwd)
            active_key = k0

        elif choice == "3":
            L = list_saved_wallets()
            if not L:
                print("🚫 Aucun wallet.")
                continue
            for i,n in enumerate(L,1):
                print(f"  {i}) {n}")
            idx = int(input("n° : ").strip()) - 1
            name = L[idx]
            pwd = getpass.getpass("Mot de passe AES : ")
            t, sec = load_wallet(name, pwd)
            if t == "mnemonic":
                k0 = derive_key0_from_mnemonic(sec)
            elif t == "wif":
                k0 = derive_key0_from_wif(sec)
            else:
                k0 = derive_key0_from_xprv(sec)
            wif = Key(import_key=k0.private_hex, network="bitcoin").wif()
            print(f"📮 Adresse bc1… : {k0.address()}")
            print("🔑 WIF        :", wif)
            active_key = k0

        elif choice == "4":
            sys.exit(0)
        else:
            continue

        # boucle après activation
        while True:
            print(f"""
--- Wallet actif [{active_key.address()}] ---
a) UTXO & solde
b) Envoyer BTC
c) Retour
""")
            o = input("Option : ").strip().lower()
            if o == "a":
                show_utxos_for_key(active_key)
            elif o == "b":
                utxos = show_utxos_for_key(active_key)
                if not utxos:
                    continue
                dest = input("Destinataire (bc1…) : ").strip()
                amt = int(float(input("Montant BTC : ").strip()) * 1e8)
                fee = int(float(input("Frais BTC [0.0001] : ").strip() or 0.0001) * 1e8)
                raw = build_and_sign_tx(active_key, utxos, dest, amt, fee)
                if raw:
                    txid = broadcast_with_curl(raw)
                    print("✅ TXID :", txid or "Échec broadcast")
            else:
                break

if __name__ == "__main__":
    main()
