from flask import Flask, redirect, url_for, render_template, request
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import datetime as dt
import base64
from io import BytesIO
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
# Try to load saved client credentials
gauth.LoadCredentialsFile("mycreds.txt")

if gauth.credentials is None:
    # Authenticate if they're not there

    # This is what solved the issues:
    gauth.GetFlow()
    gauth.flow.params.update({'access_type': 'offline'})
    gauth.flow.params.update({'approval_prompt': 'force'})

    gauth.LocalWebserverAuth()

elif gauth.access_token_expired:

    # Refresh them if expired

    gauth.Refresh()
else:

    # Initialize the saved creds

    gauth.Authorize()

# Save the current credentials to a file
gauth.SaveCredentialsFile("mycreds.txt")

drive = GoogleDrive(gauth)
images_file_id = '1J6Cbzo3L4ZELWl-I4cQxOH93nqGSmvA5'

Nombre_velo = 10

scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name('secret_sheet.json', scope)

client = gspread.authorize(creds)

sheet = client.open('SDP_Test').sheet1


def insertion(reservation):
    """
    :param reservation: liste [nom, pnom, date, numvelo, etat_reservation, datetime]
    :return: void
    place la réservation dans le spreasheet sdp
    """
    request_data = sheet.get_all_values()
    LastLineNumber = len(request_data) + 1
    sheet.insert_row(reservation, LastLineNumber)
    sheet.sort((3, 'des'))


def ejection(reservation):

    request_data = sheet.get_all_values()
    df = pd.DataFrame(request_data)
    df.columns = ['Nom', 'Prénom', 'date', 'datetime']
    flag = False

    for i in df.index:
        if [df['Nom'][i], df['Prénom'][i], df['date'][i]] == reservation[0:3]:
            LineNumber = i+1
            sheet.delete_rows(LineNumber)
            flag = True

    sheet.sort((3, 'des'))
    return flag


def available(date):

    request_data = sheet.get_all_values()
    df = pd.DataFrame(request_data)
    if len(df) == 0 :
        return True
    df.columns = ['Nom', 'Prénom', 'date', 'datetime']
    N = 0
    for i in df.index:
        if df['date'][i] == date :
            N += 1
        if N == Nombre_velo :
            return False
    return True


def render_picture(data):

    render_pic = base64.b64encode(data).decode('ascii')
    return render_pic


def ajout_photo(img, img_name):

    gfile = drive.CreateFile({'parents': [{'id': images_file_id}], 'title': img_name})
    # Read file and set it as the content of this instance.
    gfile.SetContentString(img)
    gfile.Upload()  # Upload the file.


app = Flask(__name__)


@app.route("/")
def home():

    return render_template("home.html")


@app.route("/login")
def login():
    return render_template("reservation.html")


@app.route("/login", methods=["POST", "GET"])
def reservation():
    if request.method == "POST":
        user_name = request.form["nm"]
        user_pname = request.form["pm"]
        user_date = request.form["dt"]

        today = dt.datetime.now()
        date = dt.datetime.strptime(user_date, '%Y-%m-%d')

        if available(user_date) and (date > today):
            reservation = [str(user_name).lower(), str(user_pname).lower(), str(user_date), str(dt.datetime.now())]
            insertion(reservation)
            return validation(user_name, user_pname, user_date)
        else :
            return invalidation(user_date)
    else:
        return render_template("home.html")


@app.route("/logout")
def logout():
    return render_template("logout.html")


@app.route("/logout", methods=["POST", "GET"])
def rendre_velo():
    if request.method == "POST":
        user_name = request.form["nm"]
        user_pname = request.form["pm"]
        user_date = request.form["dt"]
        image = request.files["image"]
        data = image.read()
        data = render_picture(data)
        im = BytesIO(base64.b64decode(data))
        img_name = str(user_name) + '_' + str(user_date) + '.png'

        reservation = [str(user_name).lower(), str(user_pname).lower(), str(user_date)]
        supp = ejection(reservation)
        if supp:
            ajout_photo(str(im.getvalue()), img_name)
            return validation_suppression()

        else:
            return invalidation_suppression()

    else:
        return render_template("home.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/<validation>")
def validation(nm,pm,dt):
    return f"""<p2>Demande de prêt enregistrée au nom de <I><B>{nm} {pm} </B> le <B>{dt}</B></I> </p2>""" \
           f""" <nav><ul><li><a href="/"> Home </a></li></ul></nav>"""


@app.route("/<invalidation>")
def invalidation(date):
    return f"<p2>Pas de place pour cette date {date}, essayez une autre date svp</p2>"\
           f""" <nav><ul><li><a href="/login"> Faire une réservation </a></li></ul></nav>"""


@app.route("/<validation_suppression>")
def validation_suppression():
    return f"<p2>Le vélo a bien été rendu, au plaisir de vous revoir parmi nous ! \n Vous pouvez quitter la page ou revenir à l'accueil</p2>"\
           f"""<nav><ul><li><a href="/"> Retour à l'accueil </a></li></ul></nav>"""


@app.route("/<invalidation_suppression>")
def invalidation_suppression():
    return f"<p2>La demande n'a pas abouti, les informations sont-elles valides ?</p2>"\
           f""" <nav><ul><li><a href="/logout"> Rendre un vélo </a></li></ul></nav>"""


if __name__ == "__main__":
    app.run(debug=True)
