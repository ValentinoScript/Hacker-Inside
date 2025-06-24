import os
import sys
import win32com.client

def create_shortcut(app_path, shortcut_name="MonApp", icon_path=None):
    # 1) Récupère le chemin réel du Bureau, quelle que soit la langue de Windows
    shell = win32com.client.Dispatch("WScript.Shell")
    desktop = shell.SpecialFolders("Desktop")
    
    # 2) Construit le chemin du raccourci (doit absolument finir par .lnk)
    shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")
    
    # 3) Vérifie que l'application cible existe
    if not os.path.exists(app_path):
        print(f"⚠️ Fichier introuvable : {app_path}")
        sys.exit(1)
    
    # 4) Crée et configure le raccourci
    shortcut = shell.CreateShortcut(shortcut_path)
    shortcut.TargetPath = app_path
    shortcut.WorkingDirectory = os.path.dirname(app_path)
    if icon_path and os.path.exists(icon_path):
        shortcut.IconLocation = icon_path
    else:
        shortcut.IconLocation = app_path  # icône de l'exécutable ou du .bat
    shortcut.Save()
    
    print(f"✅ Raccourci '{shortcut_name}.lnk' créé sur le Bureau :\n   {shortcut_path}")

if __name__ == "__main__":
    # Modifie ces deux variables pour ton cas :
    chemin_app = r"C:\Hacker Inside\Hacker inside.bat"
    nom_raccourci = "Hacker Inside"
    chemin_icone = "C:\Hacker Inside\Logo.ico"
    
    create_shortcut(chemin_app, nom_raccourci, chemin_icone)
