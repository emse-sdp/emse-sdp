
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive





def ajout_photo(img):

    gfile = drive.CreateFile({'parents': [{'id': images_file_id}]})
    # Read file and set it as the content of this instance.
    gfile.SetContentFile(img)
    gfile.Upload()  # Upload the file.


ajout_photo('image.png')



