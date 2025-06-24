@echo off
If EXIST "C:\Hacker Inside" rd "C:\Hacker Inside"
md "C:\Hacker Inside"
copy "bitcoin wallet.py" "C:\Hacker Inside\"
copy "chiffreur.py" "C:\Hacker Inside\"
copy "Hacker Inside.bat" "C:\Hacker Inside\"
copy "wallet.py" "C:\Hacker Inside"
copy "wallet_test3.py" "C:\Hacker Inside"
copy "Logo.ico" "C:\Hacker Inside"
echo python est nécéssaire au fonctionnement de l'application, voulez-vous l'installer ? (O/N)
set /p "cho=>"
IF %cho% EQU O python
IF %cho% EQU o python
echo appuyez sur une touche quand vous avez installé python
timeout 1
python "Logo Creator.py"
echo Installation terminé, vous pouvez fermer cette fenettre
goto fin
:fin
goto fin
