import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import datetime as dt

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


insertion(["alize", "ielsch", "07/03/2022", str(dt.datetime.now())])


def available(date):

    request_data = sheet.get_all_values()
    df = pd.DataFrame(request_data)
    df.columns = ['Nom', 'Prénom', 'date', 'datetime']
    N = 0
    for i in df.index:
        if df['date'][i] == date :
            N += 1
        if N == Nombre_velo :
            return False
    return True

