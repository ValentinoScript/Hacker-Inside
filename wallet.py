from mnemonic import Mnemonic
from bitcoinlib.wallets import Wallet, wallet_exists, WalletError
from bitcoinlib.keys import Key

def create_wallet():
    wallet_name = input("Choisissez un nom pour votre wallet : ")
    mnemo = Mnemonic("english")
    phrase = mnemo.generate(strength=128)
    w = Wallet.create(name=wallet_name, keys=phrase, network='bitcoin')
    addr = w.get_key().address
    return wallet_name, phrase, addr

def load_wallet(wallet_name):
    try:
        w = Wallet(wallet_name)
        addr = w.get_key().address
        return w, addr
    except Exception as e:
        print("Erreur chargement wallet :", e)
        return None, None

def import_wallet_from_mnemonic(wallet_name=None):
    """
    Importe un wallet à partir d'une phrase mnémonique BIP39.
    Retourne (wallet, address) ou (None, None) si erreur.
    """
    # 1) Choix / vérification du nom
    if not wallet_name:
        while True:
            wallet_name = input("Nom à donner au wallet importé : ").strip()
            if wallet_exists(wallet_name):
                print("⚠️ Le wallet '{wallet_name}' existe déjà. Choisissez-en un autre.")
            else:
                break

    # 2) Saisie de la phrase mnémonique
    phrase = input("Entrez votre phrase mnémonique (12–24 mots) : ").strip()

    # 3) Création du wallet
    try:
        w = Wallet.create(name=wallet_name, keys=phrase, network='bitcoin')
    except WalletError as e:
        print("❌ Impossible d'importer le wallet :", e)
        return None, None

    # 4) Récupération de l'adresse par défaut
    addr = w.get_key().address
    print(f"✅ Wallet '{wallet_name}' importé, adresse par défaut : {addr}")
    return w, addr

def import_wallet_from_wif(wallet_name=None):
    if not wallet_name:
        wallet_name = input("Nom pour ce wallet : ").strip()

    wif = input("Entrez votre clé privée WIF : ").strip()

    try:
        # 1) On importe la clé sans présupposer le script_type
        k = Key(import_key=wif, network='bitcoin')
        # 2) On force ici l'encodage Bech32 + P2WPKH (adresse native SegWit)
        addr = k.address(encoding='bech32', script_type='p2wpkh')  
        print(f"✅ Clé privée importée, adresse SegWit native : {addr}")

        # 3) Facultatif : enregistrer ce Key dans un Wallet pour le gérer ultérieurement
        w = Wallet.create(wallet_name,
                          keys=k,
                          network='bitcoin',
                          witness_type='segwit')  # stockage en native SegWit aussi
        print(f"✅ Wallet '{wallet_name}' créé avec succès")
    except WalletError as e:
        print("❌ Erreur d'importation :", e)
        return None, None

    return w, addr