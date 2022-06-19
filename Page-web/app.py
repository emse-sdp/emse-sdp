"""

APPLICATION WEB DU SYSTÈME DE PRÊT MINES SANS VOITURE (2021-2022)

"""
# Import des packages
from flask import Flask, redirect, url_for, render_template, request
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import datetime as dt
import base64
from io import BytesIO
import datetime
from googleapiclient.http import MediaInMemoryUpload
import pickle
import os
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build


# Constante globale
Nombre_velo = 10


# automatisation de la connexion au drive (nécessaire pour pouvoir stocker les images sur le drive)
def Create_Service(client_secret_file, api_name, api_version, *scopes):
    print(client_secret_file, api_name, api_version, scopes, sep='-')
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]

    cred = None

    pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'

    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        print(API_SERVICE_NAME, 'service created successfully')
        return service
    except Exception as e:
        print(e)
    return None


# identifiant du fichier où sont stockées les images
images_file_id = '1J6Cbzo3L4ZELWl-I4cQxOH93nqGSmvA5'
scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

# connexion au drive pour pouvoir ouvrir les spreadsheet
creds = ServiceAccountCredentials.from_json_keyfile_name('secret_sheet.json', scope)
client = gspread.authorize(creds)
sheet = client.open('SDP_Test').sheet1
code_sheet = client.open('SDP_Code').sheet1


# connexion au drive pour pouvoir stocker les images
Client_secret = "client_secrets.json"
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ["https://www.googleapis.com/auth/drive"]
service = Create_Service(Client_secret, API_NAME, API_VERSION, SCOPES)


def insertion(reservation):
    """
    :param reservation: liste [nom, pnom, date, numvelo, etat_reservation, datetime]
    :return: void
    place la réservation dans la spreasheet
    """
    request_data = sheet.get_all_values()
    LastLineNumber = len(request_data) + 1
    sheet.insert_row(reservation, LastLineNumber)
    sheet.sort((3, 'des'))


def ejection(reservation):
    """
    :param reservation: liste [nom, pnom, date, numvelo, etat_reservation, datetime]
    :return: bool
    supprime la réservation si elle est présente sur la spreadsheet et trie la spreadsheet
    """
    request_data = sheet.get_all_values()
    df = pd.DataFrame(request_data)
    df.columns = ['Nom', 'Prénom', 'date', 'datetime', 'bike_Num']
    flag = False
    for i in df.index:
        if [df['Nom'][i], df['Prénom'][i], df['date'][i], df['bike_Num'][i]] == reservation[0:4]:
            LineNumber = i+1
            sheet.delete_rows(LineNumber)
            flag = True
    sheet.sort((3, 'des'))
    return flag


def available(date):
    """
    :param date : date de réservation
    :return: bool, int
    vérifie si pour la date fournis des vélos sont disponible et renvoie le
    numéro du premier vélo disponible et un booléen
    """
    request_data = sheet.get_all_values()
    df = pd.DataFrame(request_data)
    if len(df) == 0 :
        return True, 1
    df.columns = ['Nom', 'Prénom', 'date', 'datetime', 'bike_Num']
    N = 0
    bike_avail = [i for i in range(1,11)]
    for i in df.index:
        if df['date'][i] == date :
            N += 1
            bike_avail.remove(int(df['bike_Num'][i]))
        if N == Nombre_velo :
            return False, -1
    return True, bike_avail[0]


def ajout_photo(img, img_name):
    """
    :param img : bytearray / img_name : str
    :return: void
    ajoute l'image fournie au drive sous le nom img_name
    """
    file_name = img_name
    file_meta = {
        'name': file_name,
        'parents': [images_file_id]
    }

    media = MediaInMemoryUpload(img)
    service.files().create(
        body=file_meta,
        media_body=media,
        fields='id'
    ).execute()


def get_code(bike_Num):
    """
    :param bike_Num : int
    :return: int
    renvoie le code du vélo numéro bike_Num
    """
    request_data = code_sheet.get_all_values()
    df = pd.DataFrame(request_data)
    df.columns = ['Bike_Code']
    return df['Bike_Code'][bike_Num]


# création de l'application web grâce à flask
app = Flask(__name__)


# affichage de la page d'accueil
@app.route("/")
def home():
    return render_template("home.html")


# affichage de la page des réservations
@app.route("/login")
def login():
    return render_template("reservation.html")

# la méthode post permet de récupérer les input de l'utilisateur
@app.route("/login", methods=["POST", "GET"])
def reservation():
    if request.method == "POST":
        # récupération des inputs
        user_name = request.form["nm"]
        user_pname = request.form["pm"]
        user_date = request.form["dt"]
        # on compare la date au jour actuel
        today = dt.datetime.now()
        date = dt.datetime.strptime(user_date, '%Y-%m-%d')
        # on vérifie s'il existe un vélo disponible
        avail, bike_Num = available(user_date)
        # si oui on ajoute la réservation
        if avail and (date > today):
            reservation = [str(user_name).lower(), str(user_pname).lower(), str(user_date), str(dt.datetime.now()), str(bike_Num)]
            insertion(reservation)
            code = get_code(bike_Num)
            return validation(user_name, user_pname, user_date, bike_Num, code)
        # si non on renvoie la page d'invalidation
        else :
            return invalidation(user_date)
    # si jamais on renvoie quand même la page d'acceuil
    else:
        return render_template("home.html")


# affichage de la page de deconnection
@app.route("/logout")
def logout():
    return render_template("logout.html")


# fonction pour rendre le vélo et stocke l'image sur le drive
@app.route("/logout", methods=["POST", "GET"])
def rendre_velo():
    if request.method == "POST":
        # on récupère les inputs
        user_name = request.form["nm"]
        user_pname = request.form["pm"]
        user_date = request.form["dt"]
        bike_Num = request.form["bn"]
        image = request.files["image"]
        # on transforme l'image en bite
        data = image.read()
        im = bytearray(data)
        img_name = str(user_name) + '_' + str(user_date) + '.png'
        reservation = [str(user_name).lower(), str(user_pname).lower(), str(user_date), str(bike_Num)]
        # on test la suppression
        supp = ejection(reservation)
        # si oui on stocke l'image
        if supp:
            ajout_photo(im, img_name)
            return validation_suppression()
        # sinon en renvoie la page d'invalidation
        else:
            return invalidation_suppression()
    # si jamais on renvoie quand même la page d'acceuil
    else:
        return render_template("home.html")


# affichage de la page de contact
@app.route("/contact")
def contact():
    return render_template("contact.html")


# affichage de la validation de la réservation du numéros du vélo et du code du vélo
@app.route("/<validation>")
def validation(nm,pm,dt,bn,bc):
    return f"""<p2>Demande de prêt enregistrée au nom de <I><B>{nm} {pm} </B> le <B>{dt}</B></I> <br> Le numéros du vélo est <B>{bn}<B><br> Le code du vélo est <B>{bc}<B></p2>""" \
           f""" <nav><ul><li><a href="/"> Home </a></li></ul></nav>"""

# affichage de la page d'invalidation
@app.route("/<invalidation>")
def invalidation(date):
    return f"<p2>Pas de place pour cette date {date}, essayez une autre date svp</p2>"\
           f""" <nav><ul><li><a href="/login"> Faire une réservation </a></li></ul></nav>"""


# affichage de la page de validation de la suppression de la réservation
@app.route("/<validation_suppression>")
def validation_suppression():
    return f"<p2>Le vélo a bien été rendu, au plaisir de vous revoir parmi nous ! \n Vous pouvez quitter la page ou revenir à l'accueil</p2>"\
           f"""<nav><ul><li><a href="/"> Retour à l'accueil </a></li></ul></nav>"""


# affichage de la page de d'invalidation de la suppression de la réservation
@app.route("/<invalidation_suppression>")
def invalidation_suppression():
    return f"<p2>La demande n'a pas abouti, les informations sont-elles valides ?</p2>"\
           f""" <nav><ul><li><a href="/logout"> Rendre un vélo </a></li></ul></nav>"""


# création de l'application web
if __name__ == "__main__":
    app.run(debug=True)
