import os

class DevelopmentConfig():
    DEBUG = True
    MYSQL_HOST = "localhost"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = ""
    MYSQL_DB = "proyecto_hub"
    
    #ruta para imagenes
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'statics', 'images')
    
config = {
        'development' : DevelopmentConfig
        }