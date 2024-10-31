from flask import jsonify, request, g
import os # para acceder a directorios
import re # expresiones regulares
from werkzeug.utils import secure_filename # seguridad de nombre en un archivo
import uuid #dar nombre unico a archivos
import hashlib # hash de imagen o archivo para evitar duplicados
import glob # buscar nombre entre archivos


def find_user_by_id(cursor, user_id):
    cursor.execute("SELECT id FROM usuarios WHERE id = %s", (user_id,))
    return cursor.fetchone()

def role_find_and_validate(user_id_by_admin, id_token, role_token):
    try:
        cursor=g.conexion.connection.cursor()

        #permisos de administrador
        if role_token == 1:                        
            if user_id_by_admin == None:
                user_id = id_token
                return {"id": None , "mensaje":"Debe proporcinar un id de usuario" }
            
            if user_id_by_admin < 1 or not isinstance(user_id_by_admin, int):
                return {"id" : None, "mensaje" : "Debe proporcionar un id valido"}
                        
            else:
                user_id = user_id_by_admin
                user_id_bbdd = find_user_by_id(cursor, user_id)
                if user_id_bbdd is None:
                    return {"id" : None, "mensaje" : "Usuario no encontrado"}
                else:                
                    return {"id" : user_id}
        
        #permisos de usuario
        else:
            if user_id_by_admin:
                return {"id" : None, "mensaje" : "el formato de la consulta es erroneo"}
            user_id_bbdd = find_user_by_id(cursor, id_token)            
            if user_id_bbdd is None:
                return {"id" : None, "mensaje" : "Usuario no encontrado"}
            else:
                return {"id" : id_token} 
            
    except Exception as ex:
        g.conexion.connection.rollback()
        raise ex    
    # finally:
    #     cursor.close()


def validar_datos_generica(cursor, validaciones):
    for campo, (funcion, *args) in validaciones.items():
        if args[0] is None:  # Si el valor es None, no validar
            continue

        error_al_validar = funcion(*args)
        
        if error_al_validar:
            return error_al_validar
    return None


def validar_alpha(dato_usuario, campo_bbdd):
    if not dato_usuario.isalpha():
        dato_invalido = {"mensaje": f" El {campo_bbdd} no cumple con el formato establecido", 
                         "dato_invalido" : campo_bbdd}
        return dato_invalido
    return None

def validar_comma_en_list(dato_usuario, campo_bbdd):
    for dato in dato_usuario:
        if "," in dato:
            dato_invalido = {"mensaje": f" La lista de {campo_bbdd} no cumple con el formato establecido", 
                            "dato_invalido" : campo_bbdd}
            return dato_invalido
    return None


def validar_alfanumerico(dato_usuario, campo_bbdd):
    if not dato_usuario.isalnum():
        dato_invalido = {"mensaje": f" El {campo_bbdd} no cumple con el formato establecido", 
                         "dato_invalido" : campo_bbdd}
        return dato_invalido
    return None


def validar_y_verificar_email(email, campo_bbdd, cursor):  
    
    patron = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(patron, email):
        dato_invalido = {"mensaje": f" El {campo_bbdd} no cumple con el formato establecido", 
                         "dato_invalido" : campo_bbdd}
        return dato_invalido
        
    try:        
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            return {"mensaje": "El email ya se encuentra registrado" }
                
    except Exception as ex:       
        return {"mensaje": "Error al actualizar el usuario", "error": str(ex)} 
    
    return None


def validar_email(email, campo_bbdd):  
    
    patron = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(patron, email):
        dato_invalido = {"mensaje": f" El email no cumple con el formato establecido", 
                         "dato_invalido" : campo_bbdd}
        return dato_invalido

def verificar_email(email, cursor):
    try:        
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        resultado = cursor.fetchone()
        if resultado:
            return {"mensaje": "El email se encuentra registrado", "id" : resultado[0]}
        else:            
            return {"mensaje": "El email no está registrado", "error" : "usuario no existe"}
                
    except Exception as ex:       
        return {"mensaje": "Error al buscar el usuario, intente nuevamente", "error": str(ex)} 
   


def verificacion_con_bbdd(id_user, verificar_con_bbdd, info_user_bbdd):    

    datos_distintos = {}
        
    for key, dato in verificar_con_bbdd.items():
        
        if isinstance(dato, list):
           
            for value in dato:    
               if info_user_bbdd[key] == None or value not in info_user_bbdd[key]:
                    if key not in datos_distintos:
                        datos_distintos[key] = {"update": [], "delete": []}
                    datos_distintos[key]["update"].append(value)
            
            if info_user_bbdd[key] != None:
                for value in info_user_bbdd[key]:
                    if value not in dato:
                            if key not in datos_distintos:
                                datos_distintos[key] = {"update": [], "delete": []}
                            datos_distintos[key]["delete"].append(value)
            

        elif dato != info_user_bbdd[key]:
            datos_distintos[key] = dato

    return datos_distintos

def calcular_hash(image):
    # Lee el contenido del archivo de imagen
    file_data = image.read()
    
    # Genera un hash SHA-256 del archivo
    hash_obj = hashlib.sha256()
    hash_obj.update(file_data)
    
    # Resetear el puntero del archivo para que pueda ser leído de nuevo si es necesario
    image.seek(0)
    
    return hash_obj.hexdigest()

# Verificar si el archivo imagen es válido
def verificar_nombre_imagen(filename):    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    

def validar_imagen(image, app):
    
    if 'image' not in request.files:
        return jsonify({"mensaje": "No se ha enviado ninguna imagen"}), 400
    
    if image.filename == '':
        return jsonify({"mensaje": "No se ha seleccionado ninguna imagen"}), 400
    
    # Asegura el nombre del archivo
    filename = secure_filename(image.filename)
    
    unic_filename = str(uuid.uuid4()) + os.path.splitext(image.filename)[1]

    # direccion donde se guarda el archivo
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unic_filename)    
   
    if verificar_nombre_imagen(filename):
        image.save(file_path)
        return file_path, None      
    else:
        return jsonify({"mensaje": "formato de imagen invalida"}), 400



def imagen_validar_verificar_guardar(image, usuario_id, app):
       
    if 'image' not in request.files:
        return jsonify({"mensaje": "No se ha enviado ninguna imagen"}), 400
    
    if image.filename == '':
        return jsonify({"mensaje": "No se ha seleccionado ninguna imagen"}), 400
    
    # Asegura el nombre del archivo
    filename = secure_filename(image.filename)
    
    # Extrae la extensión del archivo de la nueva imagen
    extension = os.path.splitext(filename)[1]
    
    # Nombre de archivo basado en el id del usuario
    unic_filename = f"usuario_{usuario_id}{extension}"

    # Dirección donde se guardará el nuevo archivo
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unic_filename)

    # Busca y elimina cualquier imagen existente del usuario con cualquier extensión
    old_images_pattern = os.path.join(app.config['UPLOAD_FOLDER'], f"usuario_{usuario_id}.*")
    old_images = glob.glob(old_images_pattern)

    for old_image in old_images:
        os.remove(old_image)  # Elimina la imagen anterior
    
    # Guarda la nueva imagen
    image.save(file_path)
    
    return file_path

def verificar_longitud_informacion(informacion, campo_bbdd):

    # verificar que no use caracteres prohibidos
    if verificar_texto(informacion):
        dato_invalido = {"mensaje":"La biografía contiene caracteres no permitidos.", "dato invalido": campo_bbdd}
        return dato_invalido
    
    # Validar longitud del texto (opcional)
    MAX_LENGTH = 500
    if len(informacion) > MAX_LENGTH:
        dato_invalido = {"mensaje":"no puede exeder los 500 caracteres", "dato invalido": campo_bbdd}
        return dato_invalido
    
    return None

def verificar_texto (texto):
    # Caracteres prohibidos en HTML y SQL 
    caracteres_no_permitidos = r'[<>\"\'&]|--|/\*|\*/|\x00-\x1F|\\'
    
    if re.search(caracteres_no_permitidos, texto):        
        return True
    

