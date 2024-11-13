import os

class DevelopmentConfig():
    DEBUG = True
    
    #configuracion BBDD
    MYSQL_HOST = "localhost"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = ""
    MYSQL_DB = "proyecto_hub"
        
    #configuracion envio de email
    MAIL_SERVER = 'smtp.gmail.com'  # Cambia esto según tu proveedor de correo
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'federico.tasso.musica@gmail.com'
    MAIL_PASSWORD = 'ndlr vqef etdj zrtw'
    MAIL_DEFAULT_SENDER = 'federico.tasso.musica@gmail.com'
    MAIL_TIMEOUT = 20
    MAIL_DEBUG = True 
 

    #ruta para imagenes
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'statics', 'images')

   
config = {
        'development' : DevelopmentConfig
        }