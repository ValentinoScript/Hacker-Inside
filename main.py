from wallet import create_wallet, load_wallet
from api import get_balance, broadcast_transaction
from wallet import import_wallet_from_mnemonic, import_wallet_from_wif

def menu():
    print("=== Bitcoin Wallet CLI ===")
    print("1. Créer un nouveau wallet")
    print("2. Charger un wallet existant")
    print("3. Importer un wallet existant (mnémonique)")
    print("4. Importer un wallet existant (WIF)")

    return input("Choix : ")

def wallet_menu(wallet, address):
    while True:
        print(f"\n=== Wallet [{address}] ===")
        print("1. Afficher le solde")
        print("2. Envoyer des BTC")
        print("3. Retour")
        choix = input("Choix : ")

        if choix == "1":
            solde = get_balance(address)
            print(f"Solde : {solde:.8f} BTC")
        elif choix == "2":
              dest = input("Adresse destinataire : ").strip()
              amount = float(input("Montant BTC : "))             # par ex. 0.0001
              fee = float(input("Frais BTC (optionnel) : ") or 0.00001)

              # conversion en satoshis
              amount_sat = int(amount * 1e8)
              fee_sat = int(fee    * 1e8)

              # 1) Création & signature sans diffusion
              tx = wallet.send_to(dest, amount_sat, fee=fee_sat, broadcast=False)
              print(">> TX CRÉÉE (raw hex) :", tx.rawtx)

              # 2) Diffusion « manuelle » via BlockCypher API
              from api import broadcast_transaction
              res = broadcast_transaction(tx.rawtx)
              print(">> Résultat diffusion :", res)

              # — ou pour tout faire d’un coup —
              tx2 = wallet.send_to(dest, amount_sat, fee=fee_sat, broadcast=True)
              print(">> TXID :", tx2.txid)
        else:
            break

def main():
    while True:
        choix = menu()
        if choix == "1":
            name, phrase, addr = create_wallet()
            print(f"\n✅ Wallet '{name}' créé avec succès !")
            print("📒 Phrase mnémonique (sauvegardez-la précieusement) :", phrase)
            print("📮 Adresse Bitcoin :", addr)

        elif choix == "2":
            name = input("Nom du wallet : ")
            wallet, addr = load_wallet(name)
            if wallet:
                wallet_menu(wallet, addr)

        elif choix == "3":
            wallet, addr = import_wallet_from_mnemonic()
            if wallet: wallet_menu(wallet, addr)

        elif choix == "4":
            wallet, addr = import_wallet_from_wif()
            if wallet: wallet_menu(wallet, addr)

        else:
            break

if __name__ == "__main__":
    main()