import string
import hashlib
from cryptography.fernet import Fernet
from Crypto.Cipher import AES
import base64

def cesar_cipher(text, key, decrypt=False):
    """Chiffre ou déchiffre un message avec le chiffrement de César."""
    if decrypt:
        key = -key  # Inversion de la clé pour déchiffrer
    
    alphabet = string.ascii_letters + string.digits + string.punctuation + " "
    shifted_alphabet = alphabet[key:] + alphabet[:key]
    table = str.maketrans(alphabet, shifted_alphabet)
    return text.translate(table)

def xor_cipher(text, key):
    """Chiffre/Déchiffre un message avec XOR."""
    return ''.join(chr(ord(char) ^ key) for char in text)

def fernet_encrypt(text, key):
    """Chiffre un message avec Fernet."""
    cipher = Fernet(key)
    return cipher.encrypt(text.encode()).decode()

def fernet_decrypt(text, key):
    """Déchiffre un message avec Fernet."""
    cipher = Fernet(key)
    return cipher.decrypt(text.encode()).decode()

def pad(s):
    """Ajoute un padding pour AES (bloc de 16 octets)."""
    return s + (16 - len(s) % 16) * chr(16 - len(s) % 16)

def unpad(s):
    """Retire le padding après déchiffrement AES."""
    return s[:-ord(s[-1])]

def aes_encrypt(text, key):
    """Chiffre un message avec AES en mode CBC."""
    key = hashlib.sha256(key.encode()).digest()  # Hash de la clé pour obtenir 32 octets
    iv = b'1234567890123456'  # IV statique (mieux de le rendre aléatoire et de l'envoyer avec le message)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(text).encode())
    return base64.b64encode(iv + encrypted).decode()

def aes_decrypt(text, key):
    """Déchiffre un message avec AES en mode CBC."""
    key = hashlib.sha256(key.encode()).digest()
    encrypted = base64.b64decode(text)
    iv = encrypted[:16]  # Récupération de l'IV
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(encrypted[16:]).decode())
    return decrypted

def main():
    print("Choisissez une méthode :")
    print("1. Chiffrement César")
    print("2. Chiffrement XOR")
    print("3. Chiffrement Fernet (AES)")
    print("4. Chiffrement AES (CBC)")
    
    choix = input("Entrez 1, 2, 3 ou 4 : ")
    action = input("Voulez-vous chiffrer ou déchiffrer ? (c/d) : ")
    
    if action == "c":
        message = input("Entrez le message à chiffrer : ")
    else:
        message = input("Entrez le message chiffré : ")
    
    if choix == "1":
        key = int(input("Entrez une clé (nombre entier) : "))
        if action == "c":
            encrypted = cesar_cipher(message, key)
            print(f"Message chiffré : {encrypted}")
        else:
            decrypted = cesar_cipher(message, key, decrypt=True)
            print(f"Message déchiffré : {decrypted}")
    
    elif choix == "2":
        key = int(input("Entrez une clé (nombre entier entre 1 et 255) : "))
        if action == "c":
            encrypted = xor_cipher(message, key)
            print(f"Message chiffré : {encrypted}")
        else:
            decrypted = xor_cipher(message, key)
            print(f"Message déchiffré : {decrypted}")
    
    elif choix == "3":
        key = input("Entrez votre clé Fernet : ")
        key = key.encode()
        if action == "c":
            encrypted = fernet_encrypt(message, key)
            print(f"Message chiffré : {encrypted}")
        else:
            decrypted = fernet_decrypt(message, key)
            print(f"Message déchiffré : {decrypted}")
    
    elif choix == "4":
        key = input("Entrez une clé secrète : ")
        if action == "c":
            encrypted = aes_encrypt(message, key)
            print(f"Message chiffré : {encrypted}")
        else:
            decrypted = aes_decrypt(message, key)
            print(f"Message déchiffré : {decrypted}")
    
    else:
        print("Choix invalide.")
        return

if __name__ == "__main__":
    main()
