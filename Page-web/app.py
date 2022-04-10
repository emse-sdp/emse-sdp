from flask import Flask, redirect, url_for, render_template, request
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import datetime as dt

Nombre_velo = 1

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
        if available(user_date) :
            reservation = [str(user_name), str(user_pname), str(user_date), str(dt.datetime.now())]
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

        reservation = [str(user_name), str(user_pname), str(user_date)]
        supp = ejection(reservation)
        if supp:
            return validation_suppression()

        else:
            return invalidation_suppression()

    else:
        return render_template("home.html")


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
    return f"<p2>Le vélo a bien été rendu, au plaisir de vous revoir parmi nous ! \n vous pouvez quitter la page ou revenir à l'accueil</p2>"\
           f"""<nav><ul><li><a href="/"> Home </a></li></ul></nav>"""


@app.route("/<invalidation_suppression>")
def invalidation_suppression():
    return f"<p2>La demande n'a pas abouti, les information sont-elle valide ?</p2>"\
           f""" <nav><ul><li><a href="/logout"> Rendre un vélo </a></li></ul></nav>"""

if __name__ == "__main__":
    app.run(debug=True)
