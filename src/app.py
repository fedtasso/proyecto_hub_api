from flask import Flask, jsonify, request
from flask_mysqldb import MySQL 
from security import hash_password, verify_password, generate_auth_token, verify_auth_token, token_required, admin_can_modify, token_id_recuperar_password
from config import config
import os # para acceder a directorios
import re # expresiones regulares
from werkzeug.utils import secure_filename # seguridad de nombre en un archivo
import uuid #dar nombre unico a archivos
import hashlib # hash de imagen o archivo para evitar duplicados
import glob # buscar nombre entre archivos
from flask_mail import Mail, Message # enviar email
import validators


app = Flask(__name__)

#cargar configuraciones
app.config.from_object(config["development"])

conexion = MySQL(app)
mail = Mail(app)

# El admin debe enviar el id del usuario que desea modificar
# El admin debe enviar su id para poder modificar su contraseña.
# En GET usuarios, desde el front se puede enviar solo nombre, solo apellido, nombre y apellido o ningun dato

#----------Pendientes
#revisar todo los status 200,300,400,500
# hacer que admin solo pueda modificar contraseña
# usuarios rol 2, si envian email retornar error en formato de id


# valida(comprueba si info es valida) verificar (busca en bbdd)


###################### PASAR A OTRO ARCHIVO ##################



def find_user_by_id(cursor, user_id):
    cursor.execute("SELECT id FROM usuarios WHERE id = %s", (user_id,))
    return cursor.fetchone()

def find_user_by_email(cursor, email):#no estoy validando el formato del email
    # patron = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    #     if not re.match(patron, email):
    #         dato_invalido = {"mensaje": f" El {campo_bbdd} no cumple con el formato establecido", 
    #                         "dato_invalido" : campo_bbdd}
    #         return dato_invalido

    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
    return cursor.fetchone()

def role_find_and_validate(user_id_by_admin, id_token, role_token):
    try:
        cursor=conexion.connection.cursor()

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
        conexion.connection.rollback()
        raise ex    
    # finally:
    #     cursor.close()

# no hace falta el cursor???
def validar_datos_generica(cursor, validaciones):
    for campo, (funcion, *args) in validaciones.items():
        if args[0] is None:  # Si el valor es None, no validar
            continue

        error_al_validar = funcion(*args)
        
        if error_al_validar:
            return error_al_validar
    return None


def validar_alpha(dato_usuario, campo_bbdd):
    if not bool(re.match(r"^[A-Za-z\s]+$", dato_usuario)):
        dato_invalido = {"mensaje": f" El {campo_bbdd} no cumple con el formato establecido", 
                         "dato_invalido" : campo_bbdd}
        return dato_invalido
    return None

def validar_comma_en_list(dato_usuario, campo_bbdd):# no esta validando que no haya caracteres especiales
    for dato in dato_usuario:
        if "," in dato:
            dato_invalido = {"mensaje": f" La lista de {campo_bbdd} no cumple con el formato establecido", 
                            "dato_invalido" : campo_bbdd}
            return dato_invalido
    return None


def validar_alfanumerico(dato_usuario, campo_bbdd): #no permite espacios
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
               if value not in info_user_bbdd[key].split(","):
                    if key not in datos_distintos:
                        datos_distintos[key] = {"update": [], "delete": []}
                    datos_distintos[key]["update"].append(value)
            
            for value in info_user_bbdd[key].split(","):
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
    

def validar_imagen(image):    
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



def imagen_validar_verificar_guardar(image, usuario_id):
       
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
    if validar_texto(informacion):
        dato_invalido = {"mensaje":"La biografía contiene caracteres no permitidos.", "dato invalido": campo_bbdd}
        return dato_invalido
    
    # Validar longitud del texto (opcional)
    MAX_LENGTH = 500
    if len(informacion) > MAX_LENGTH:
        dato_invalido = {"mensaje":"no puede exeder los 500 caracteres", "dato invalido": campo_bbdd}
        return dato_invalido
    
    return None

def validar_texto (texto):
    # Caracteres prohibidos en HTML y SQL 
    caracteres_no_permitidos = r'[<>\"\'&]|--|/\*|\*/|\x00-\x1F|\\'
    
    if re.search(caracteres_no_permitidos, texto):        
        return True

def validar_url(url, campo_bbdd):
    if not validators.url(url):
        dato_invalido = {"mensaje":"formato de url invalida", "dato invalido": campo_bbdd}
        return dato_invalido
    else:
        return None 



###################### FIN PASAR A OTRO ARCHIVO ##################



# ------- crear admin (ejecutar antes de acceder)-----------

#funcion autoejecutable
def crear_admin():
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)
        
        nombre = "usuario"
        apellido = "administrador"
        email = "admin@gmail.com"
        password = "clubdedesarroladores"


        hashed_password = hash_password(password)
        
        cursor.execute("SELECT id FROM usuarios WHERE id = %s", (1,))
        admin_existe = cursor.fetchone()

        if admin_existe:
            return {"mensaje": "el administrador existe"}
        
        else:        
            # Insertar en tabla usuarios
            sql = "INSERT INTO usuarios (nombre, apellido, email, password) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (nombre, apellido, email, hashed_password))
            usuario_id = cursor.lastrowid      
            
            # insetar en tabla roles rol admin
            rol_id = 1         
            cursor.execute("INSERT INTO roles_usuarios (usuario_id, rol_id) VALUES (%s, %s)", (usuario_id, rol_id))
            
            conexion.connection.commit()
            return {"mensaje": "administrador registrado con exito", "id": usuario_id},200    
      
    except Exception as ex: 
        conexion.connection.rollback()
        return {"mensaje": "Error al registrar el usuario", "error": str(ex)}, 500    
    finally:
        cursor.close()

admin_existe = False 

@app.before_request
def setup():
    global admin_existe # buscar alternativa para no usar gloval   
    if admin_existe == False: 
        resultado = crear_admin()
        admin_existe = True
        print(resultado)



# ---------- login -----------
@app.route('/login', methods=["POST"]) ####falta verificar pass###
def login():
    datos = request.get_json()
    email = datos.get('email')
    user_pass_front = datos.get('password')

    
    contraseña_invalida = False # hacer funcion para verificar contraseña
    email_invalido = validar_email(email, "email")
    if email_invalido or contraseña_invalida:
        return jsonify (email_invalido)

    try:
        cursor = conexion.connection.cursor()
        sql = """SELECT 
                    u.id, 
                    u.nombre,
                    u.apellido, 
                    u.password,
                    i.image,
                    ru.rol_id                     
                FROM 
                    usuarios u
                LEFT JOIN 
                    informacion i ON u.id = i.usuario_id
                LEFT JOIN 
                    roles_usuarios ru ON u.id = ru.usuario_id
                WHERE 
                    email = %s                
            """  
        cursor.execute(sql,(email,))
        usuario = cursor.fetchone() 
        if usuario is None:
             return jsonify({"mensaje":"El usuario no se encuentra registrado"}), 409
        user_pass_bbdd = usuario[3]
        if usuario and verify_password(user_pass_bbdd, user_pass_front):    
            id_user = usuario[0]
            rol = usuario[5]
            token = "Bearer " + generate_auth_token(id_user, rol)
            return jsonify({"mensaje": "login exitoso", 
                            "token":  token,
                            "datos": {"nombre" : usuario[1],
                            "apellido" : usuario[2], 
                            "imagen" : usuario[4]                          
                            }}), 200
        else:
            return jsonify({"mensaje": "contraseña inválida"}), 401  
    except Exception as ex:
        return jsonify({"mensaje": "Error al loguear el usuario", "error": str(ex)}), 500  
    finally:
        cursor.close()

# agregar url_github a crear usuario
# ------- crear usuario (json) sin imagen -----------
@app.route('/registrar_json', methods=["POST"]) #falta verificar contraseña
def registrar_json():
    datos= request.get_json()
    if datos is None:
        return jsonify({"mensaje": "No se ha enviado ninguna información"}), 400
   
    nombre = datos.get('nombre') 
    apellido = datos.get('apellido')
    email = datos.get('email')
    password = datos.get('password')
    informacion_adicional = datos.get('informacion_adicional')    
    perfiles = datos.get('perfiles')
    tecnologias = datos.get('tecnologias')  
    
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)
        print("llegamos1")    
        #validar entradas
        validaciones = {}
        
        if nombre:
            validaciones["nombre"] = (validar_alpha, nombre, "nombre")
        else:
            return jsonify ({"mensaje": " el nombre es requerido"})
        
        if apellido:
            validaciones["apellido"] = (validar_alpha, apellido, "apellido")
        else:
            return jsonify ({"mensaje": " el apellido es requerido"})

        if email:
            validaciones["email"] = (validar_y_verificar_email, email, "email", cursor)
        else:
            return jsonify ({"mensaje": " el email es requerido"})
                
        if password:
            print("falta validar password")
        else:
            return jsonify ({"mensaje": " la contraseña es requerida"})
        
        if informacion_adicional:
            validaciones["informacion_adicional"] = (verificar_longitud_informacion, informacion_adicional, "informacion_adicional")

        if perfiles:
            validaciones["perfiles"] = (validar_comma_en_list, perfiles, "perfiles")# no esta validando que no haya caracteres especiales
        
        if tecnologias:
            validaciones["tecnologias"] = (validar_comma_en_list, tecnologias, "tecnologias")# no esta validando que no haya caracteres especiales

        resultado_validacion = validar_datos_generica(cursor, validaciones)        
        if resultado_validacion:
            return jsonify(resultado_validacion), 400
       
        # Hacer hash de contraseña
        hashed_password = hash_password(password)        
       
        # Insertar en tabla usuarios
        sql = "INSERT INTO usuarios (nombre, apellido, email, password) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nombre, apellido, email, hashed_password))
        
        #recuperar id usuario
        usuario_id = cursor.lastrowid

        # insertar en tabla informacion (me aseguro que usuario e informacion tengan el mismo id)
        sql = "INSERT INTO informacion (usuario_id, informacion_adicional) VALUES (%s, %s)"
        cursor.execute(sql, (usuario_id, informacion_adicional))
        
        # insetar en tabla perfiles
        for perfil in perfiles:
            sql = "INSERT INTO perfiles (usuario_id, perfil) VALUES(%s, %s)"
            cursor.execute(sql,(usuario_id,perfil))
       
        # insertar en tabla tecnologias
        for tecnologia in tecnologias:
            cursor.execute("INSERT INTO tecnologias (usuario_id, tecnologia) VALUES (%s, %s)", (usuario_id, tecnologia))
        
        # insetar en tabla roles
        rol_id = 2 # usuario por defecto        
        cursor.execute("INSERT INTO roles_usuarios (usuario_id, rol_id) VALUES (%s, %s)", (usuario_id, rol_id))
        
        conexion.connection.commit()
        return jsonify({"mensaje": "Usuario registrado con exito", "id": usuario_id}),200    
      
    except Exception as ex: 
        conexion.connection.rollback()
        return jsonify({"mensaje": "Error al registrar el usuario", "error": str(ex)}), 500    
    finally:
        cursor.close()

# agregar url_github a crear usuario
# ---------- crear usuario (form) con imagen -----------
@app.route('/registrar', methods=["POST"]) #solo falta verificar password
def registrar():   
    nombre = request.form.get('nombre') 
    apellido = request.form.get('apellido')
    email = request.form.get('email')
    password = request.form.get('password')
    informacion_adicional = request.form.get('informacion_adicional')
    image = request.files.get('image')
    url_github = request.files.get('url_github')
    perfiles = request.form.getlist('perfiles[]')
    tecnologias = request.form.getlist('tecnologias[]')   
    
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)

        #validar entradas
        validaciones = {}
        
        if nombre:
            validaciones["nombre"] = (validar_alpha, nombre, "nombre")
        else:
            return jsonify ({"mensaje": " el nombre es requerido"})
        
        if apellido:
            validaciones["apellido"] = (validar_alpha, apellido, "apellido")
        else:
            return jsonify ({"mensaje": " el apellido es requerido"})

        if email:
            validaciones["email"] = (validar_y_verificar_email, email, "email", cursor)
        else:
            return jsonify ({"mensaje": " el email es requerido"})
        
        if url_github:
            print("falta validar url")
                
        if password:
            print("falta validar password")
        else:
            return jsonify ({"mensaje": " la contraseña es requerida"})

        if informacion_adicional:
            validaciones["informacion_adicional"] = (verificar_longitud_informacion, informacion_adicional, "informacion_adicional")

        if perfiles:
            validaciones["perfiles"] = (validar_comma_en_list, perfiles, "perfiles")# no esta validando que no haya caracteres especiales
        
        if tecnologias:#validar com otexto tambien????------------------------------------------------------------------
            validaciones["tecnologias"] = (validar_comma_en_list, tecnologias, "tecnologias")# no esta validando que no haya caracteres especiales

        resultado_validacion = validar_datos_generica(cursor, validaciones)        
        if resultado_validacion:
            return jsonify(resultado_validacion), 400
        
              # # Calcular el hash de la imagen
        # hash_archivo = calcular_hash(image)
        
        # # Verificar si la imagen ya existe en la base de datos
        # cursor.execute("SELECT image FROM informacion WHERE hash_archivo = %s", (hash_archivo,))
        # imagen_existe = cursor.fetchone()
               
        # if imagen_existe:
        #     file_path = imagen_existe[0]  # La imagen ya existe
            
        # else:
        #     # Validar y almacenar la imagen
        #     file_path, error_response = validar_imagen(image)
        #     if error_response:
        #         return error_response
       

        # Hacer hash de contraseña
        hashed_password = hash_password(password)
       
        # Insertar en tabla usuarios
        sql = "INSERT INTO usuarios (nombre, apellido, email, password) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nombre, apellido, email, hashed_password))
        usuario_id = cursor.lastrowid
        
        if image:
            file_path = imagen_validar_verificar_guardar(image, usuario_id)            
        else:  
            file_path = None
       
        # insertar en tabla informacion (me aseguro que usuario e informacion tengan el mismo id)       
        sql = "INSERT INTO informacion (usuario_id, informacion_adicional, image) VALUES (%s, %s, %s)"
        cursor.execute(sql, (usuario_id,informacion_adicional,file_path))
        
        # insetar en tabla perfiles
        for perfil in perfiles:
            sql = "INSERT INTO perfiles (usuario_id, perfil) VALUES(%s, %s)"
            cursor.execute(sql,(usuario_id,perfil))

        # insertar en tabla tecnologias
        for tecnologia in tecnologias:
            cursor.execute("INSERT INTO tecnologias (usuario_id, tecnologia) VALUES (%s, %s)", (usuario_id, tecnologia))
        
        # insetar en tabla roles
        rol_id = 2 # usuario por defecto
        cursor.execute("INSERT INTO roles_usuarios (usuario_id, rol_id) VALUES (%s, %s)", (usuario_id, rol_id))
                
        conexion.connection.commit()
        return jsonify({"mensaje": "Usuario registrado"}),200   
       
    except Exception as ex: 
        conexion.connection.rollback()
        return jsonify({"mensaje": "Error al registrar el usuario", "error": str(ex)}), 500  
      
    finally:
        cursor.close()


# ---------- actualizar imagen de tabla informacion (form)-----------
@app.route('/image', methods=["PUT"]) #terminado
@token_required
def imagen(id_token, role_token):
    
    image = request.files.get('image')
    user_id_by_admin = request.form.get('id')
    
    # buscar usuario y asignar rol
    validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
    if validated_user_id["id"] is None:
            return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
    else:
        #if hay id request enviar error de permisos 400        
        id_user = validated_user_id["id"]    
    
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)

        if image:
            file_path = imagen_validar_verificar_guardar(image, id_token)
        else:
            return jsonify({"mensaje": "debe seleccionar una imagen",}), 500    
        # insertar imagen en tabla informacion
        sql = "UPDATE informacion SET image = %s WHERE usuario_id = %s"
        cursor.execute(sql, (file_path, id_user))
              
        conexion.connection.commit()
        return jsonify({"mensaje": "imagen cargada con exito"}),200      
    except Exception as ex: 
        conexion.connection.rollback()
        return jsonify({"mensaje": "Error al cargar la imagen", "error": str(ex)}), 500    
    finally:
        cursor.close()



# ---------- mostrar participantes -----------
@app.route('/usuarios', methods=["GET"])
def mostrar_usuarios():
    nombre = request.args.get('nombre')
    apellido = request.args.get('apellido')
    try:
        cursor=conexion.connection.cursor()
        sql = """
            SELECT 
                u.id,
                u.nombre,
                u.apellido,
                u.email,                
                i.informacion_adicional,
                i.image,                
                p.perfil,
                t.tecnologia,                
                ru.rol_id,
                i.url_github                
            FROM 
                usuarios u 
            LEFT JOIN 
                informacion i ON u.id = i.usuario_id
            LEFT JOIN
                perfiles p ON u.id = p.usuario_id
            LEFT JOIN 
                tecnologias t ON u.id = t.usuario_id
            LEFT JOIN 
                roles_usuarios ru ON u.id = ru.usuario_id
            WHERE 1=1
            """
        #agregar nombre y apellido a la consulta sql
        parametros = []
        if nombre:
            sql += "AND nombre = %s"
            parametros.append(nombre)
        if apellido:
            sql += "AND apellido = %s"
            parametros.append(apellido)        
        # ejecutar consulta
        cursor.execute(sql, parametros)
        datos = cursor.fetchall()  
        if datos:
            usuarios_dict = {}        
            for user in datos:
                # verficar rol para mostrar
                if user[8] == 1:
                    rol = "admin"
                else:
                    rol = "usuario"
                user_id = user[0]
                if user_id == 1:
                    continue            
                if user_id not in usuarios_dict:
                    usuarios_dict[user_id] = {
                        "id": user_id,
                        "nombre": user[1],
                        "apellido": user[2],
                        "email": user[3],                        
                        "informacion": user[4],
                        "image": user[5],
                        "perfiles": [], 
                        "tecnologias": [],
                        "rol": rol, 
                        "url_github":user[9]
                }            
                if user[6] is not None and user[6] not in usuarios_dict[user_id]["perfiles"]:
                    usuarios_dict[user_id]["perfiles"].append(user[6])
                if user[7] is not None and user[7] not in usuarios_dict[user_id]["tecnologias"]:
                    usuarios_dict[user_id]["tecnologias"].append(user[7])        
            usuarios = list(usuarios_dict.values())       
            return jsonify({"usuarios":usuarios,"mensaje":"Todos los usuarios"}), 200
        else:
            return jsonify({"mensaje": "Usuario no encontrado"}), 404
    except Exception as ex:    
        return jsonify({"mensaje": "Error al buscar datos del usuario", "error": str(ex)}), 500    
    finally:
        cursor.close()


# ------- Update tablas --> usuarios, informacion, perfiles, tecnologias -----------
@app.route('/usuario', methods=["PUT"])
@token_required
def actualizar_usuario(id_token, role_token):

    nombre = request.form.get('nombre') 
    apellido = request.form.get('apellido')
    email = request.form.get('email')    
    informacion_adicional = request.form.get('informacion_adicional')
    image = request.files.get('image')
    perfiles = request.form.getlist('perfiles[]')
    tecnologias = request.form.getlist('tecnologias[]')   
    user_id_by_admin = request.form.get('id')
    
    try: 
        cursor=conexion.connection.cursor()      
        conexion.connection.autocommit(False)

        #validar entradas
        validaciones = {}
        
        if nombre:
            validaciones["nombre"] = (validar_alpha, nombre, "nombre")

        if apellido:
            validaciones["apellido"] = (validar_alpha, apellido, "apellido")
        
        if email:
            validaciones["email"] = (validar_email, email, "email")
        
        if informacion_adicional:
            validaciones["informacion_adicional"] = (verificar_longitud_informacion, informacion_adicional, "informacion_adicional")

        if perfiles:
            validaciones["perfiles"] = (validar_comma_en_list, perfiles, "perfiles")# no esta validando que no haya caracteres especiales
        
        if tecnologias:
            validaciones["tecnologias"] = (validar_comma_en_list, tecnologias, "tecnologias")# no esta validando que no haya caracteres especiales

        resultado_validacion = validar_datos_generica(cursor, validaciones)        
        if resultado_validacion:
            return jsonify(resultado_validacion), 400
        
        #verificar rol        
        validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)

        if validated_user_id["id"] is None:
             return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
        else:
            id_user = validated_user_id["id"]
                      
        # comparar info del front con la bbdd
        #informacion desde el front
        info_user_front = {"nombre": nombre, 
                          "apellido": apellido, 
                          "email": email,                           
                          "info_adicional": informacion_adicional, 
                          "perfiles": perfiles, 
                          "tecnologias": tecnologias
                            }      
        
        #buscar informacion del usuario en la bbdd     
        cursor.execute("""
                       SELECT u.nombre, u.apellido, u.email, i.informacion_adicional, 
                       GROUP_CONCAT(DISTINCT p.perfil SEPARATOR ',') AS perfiles,
                       GROUP_CONCAT(DISTINCT t.tecnologia SEPARATOR ',') AS tecnologias
                       FROM usuarios u
                       LEFT JOIN informacion i ON u.id = i.usuario_id
                       LEFT JOIN perfiles p ON u.id = p.usuario_id
                       LEFT JOIN tecnologias t ON u.id = t.usuario_id
                       WHERE u.id = %s
                       """, (id_user,))     
        user_bbdd = cursor.fetchone()
      
        
        info_user_bbdd = {"nombre":user_bbdd[0], 
                          "apellido":user_bbdd[1], 
                          "email":user_bbdd[2], 
                          "info_adicional":user_bbdd[3],                                                  
                          "perfiles":user_bbdd[4], 
                          "tecnologias":user_bbdd[5]
                            }
        print("info bbdd", info_user_bbdd)
        # verificar si la informacion es igual a la almacenada en BBDD  
        verificar_con_bbdd = {}
       
        for key, value in info_user_front.items():
            if value:
                verificar_con_bbdd[key] = value
            
        datos_actualizar = verificacion_con_bbdd(id_user, verificar_con_bbdd, info_user_bbdd)
        
        if image:
            datos_actualizar["image"] = image
        
        if not datos_actualizar:
            
            return jsonify ({"mensaje": "todos los datos ya existen"}), 400  
           
        if "error" in datos_actualizar:
            return jsonify(datos_actualizar), 500
        
        #verificar que el mail no este usado por otro usuario
        if "email" in datos_actualizar:
            if validar_y_verificar_email(email, "email", cursor):
                return jsonify ({"mensaje": "el mail ya existe"}), 400 
              
        # modificar informacion nueva en bbdd
        set_clause = {
              "usuarios": [],
              "informacion": [],
              "perfiles" : [],
              "tecnologias" : []
        }
        params = {
              "usuarios": [],
              "informacion": [],
              "perfiles" : [],
              "tecnologias" : [], 
        }
        
    
        if "nombre" in datos_actualizar:
            set_clause["usuarios"].append("nombre = %s")
            params["usuarios"].append(nombre)
        
        if "apellido" in datos_actualizar:
            set_clause["usuarios"].append("apellido = %s")
            params["usuarios"].append(apellido)

        if "email" in datos_actualizar:                        
            set_clause["usuarios"].append("email = %s")
            params["usuarios"].append(email)

        if "info_adicional" in datos_actualizar:
            set_clause["informacion"].append("informacion_adicional = %s")
            params["informacion"].append(informacion_adicional)

        # if "image" in datos_actualizar:
        #     # verificar si la imagen ya existe en la bbdd mediante hash   
        #     print("hash_image", hash_image)                        
        #     cursor.execute("SELECT image FROM informacion WHERE hash_archivo = %s", (hash_image,))
        #     imagen_existe = cursor.fetchone()
        #     print("imagen existe",imagen_existe)
     
        #     if imagen_existe:
        #         file_path = imagen_existe  # Si existe usa su direccion
        #         print("FILE_PATH", file_path)
                
        #     else:
        #         # Validar y almacenar la imagen
        #         file_path, error_response = validar_imagen(image)
        #         if error_response:
        #             return error_response
        print("image")
        if "image" in datos_actualizar:
            file_path = imagen_validar_verificar_guardar(image, id_token)
            set_clause["informacion"].append("image = %s")
            params["informacion"].append(file_path)
            # set_clause["informacion"].append("hash_archivo = %s")
            # params["informacion"].append(hash_image)
            print("file_path", file_path)
        else:  
            file_path = None
       

   
        # actualizar usuario
        if set_clause["usuarios"]:
            params["usuarios"].append(id_user)
            sql = f"""UPDATE usuarios
                            SET {', '.join(set_clause["usuarios"])} 
                            WHERE id = %s"""
            cursor.execute(sql, tuple(params["usuarios"]))

        # actualizar informacion
        if set_clause["informacion"]:
            params["informacion"].append(id_user)
            sql = f"""UPDATE informacion
                            SET {', '.join(set_clause["informacion"])} 
                            WHERE usuario_id = %s"""
            cursor.execute(sql, tuple(params["informacion"]))
            print(sql)
            print(tuple(params["informacion"]))

        # actualizar perfiles
        if "perfiles" in datos_actualizar:             
            for value in datos_actualizar["perfiles"]["update"]:            
                sql = """
                    INSERT INTO
                        perfiles (usuario_id, perfil)
                    VALUES
                        (%s, %s)                                                       
                """                    
                cursor.execute(sql,(id_user, value))      
        
        #borrar perfiles            
            for value in datos_actualizar["perfiles"]["delete"]:                 
                sql = """
                    DELETE FROM
                        perfiles 
                    WHERE 
                        usuario_id = %s  AND perfil = %s                                                     
                """
                cursor.execute(sql,(id_user, value)) 

         # actualizar tecnologias
        if "tecnologias" in datos_actualizar:             
            for value in datos_actualizar["tecnologias"]["update"]:            
                sql = """
                    INSERT INTO
                        tecnologias (usuario_id, tecnologia)
                    VALUES
                        (%s, %s)                                                       
                """                    
                cursor.execute(sql,(id_user, value))      
        
        #borrar tecnologias            
            for value in datos_actualizar["tecnologias"]["delete"]:                 
                sql = """
                    DELETE FROM
                        tecnologias 
                    WHERE 
                        usuario_id = %s  AND tecnologia = %s                                                     
                """
                cursor.execute(sql,(id_user, value)) 


        conexion.connection.commit()
        return jsonify({"mensaje": "Datos actualizados"}), 200        
    except Exception as ex:        
        conexion.connection.rollback()
        return jsonify({"mensaje": "Error al actualizar el usuario", "error": str(ex)}), 500
    finally:
        cursor.close()


# ------- Delete usuario join todas las tablas   -----------
@app.route('/usuario', methods=["DELETE"])
@token_required
def borrar_usuario(id_token, role_token):
    datos= request.get_json(silent=True)
    
    try:
        cursor=conexion.connection.cursor()
        print(datos)
      
       
        #verificar si es admin o user       
        if datos:   
            user_id_by_admin = datos.get('id')             
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
            if validated_user_id["id"] is None:
                return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404            
            else:
                id_user = validated_user_id["id"]
        
        else:
            user_id_by_admin = None     
            validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
            if validated_user_id["id"] is None:
                return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
            else:
                id_user = id_token
        
       
        #Borrar usuario
        sql = "DELETE FROM usuarios WHERE id = %s"
        cursor.execute(sql,(id_user,))
        conexion.connection.commit()
        return jsonify({"mensaje":"Has eliminado el usuario"}), 200
    
    except Exception as ex:
        return jsonify({"mensaje":"error al eliminar el usuario", "error": str(ex)}), 500
    finally:
        cursor.close()


# el user admin para cambiar su password debe enviar el id 1
#-------------- actualizar_password -----------------
@app.route('/actualizar_password', methods=["PUT"])
@token_required
def actualizar_password(id_token, role_token):
    password = request.form.get("password")
    user_id_by_admin = request.form.get("id")
    try:
        cursor = conexion.connection.cursor()
        
        #verificar si es admin o user               
        validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
        if validated_user_id["id"] is None:
            return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404            
        else:
            id_user = validated_user_id["id"]
        print(id_user)      
        
        if password:

            #falta validar password
         
            #seleccionas pass de bbdd
            cursor.execute("SELECT password FROM usuarios WHERE id = %s", (id_user,))
            password_bbdd = cursor.fetchone()
            
            #verficar que el password sea distinto al almacenado
            if verify_password(password_bbdd[0], password):
                return jsonify ({"mensaje": "la contraseña es identica a la actual"}), 400
            #actualizar password
            else:
                hashed_password = hash_password(password)                
                cursor.execute("UPDATE usuarios SET password = %s where id = %s", (hashed_password, id_token))
                conexion.connection.commit()
                return jsonify ({"mensaje": "contraseña actualizada con exito"}), 200
            
    except Exception as ex:
        return jsonify({"mensaje":"error al actualizar la contraseña", "error": str(ex)}), 500
    
    finally:
        cursor.close()


#---------------------------------------------------------------------

@app.route('/recuperar_password', methods=["POST"])
def recuperar_password():
    email = request.form.get("email")

    try:
        cursor = conexion.connection.cursor()
     
        if email:
            #validar formato de mail
            email_invalido = validar_email(email, "email")
            if email_invalido:
                return jsonify (email_invalido)

            #buscar en bbdd
            mail_existe = verificar_email(email, cursor)
            
            if "error" in mail_existe:
                return jsonify(mail_existe), 400
            
            usuario_id = mail_existe["id"]
            
            #crear token_id
            token_id = token_id_recuperar_password(usuario_id)
            
            #almacenar los token en la bbdd
            cursor.execute("INSERT INTO recuperar_password(usuario_id, token_id) VALUES (%s, %s)",(usuario_id, token_id))

            #crear mensaje
            msg = Message ("Recuperar contraseña",                  
            recipients=[f"{email}"],
            body = f"""
Nos comunicamos desde el Club de Desarrolladores de Vicente López.
            
Para recuperar su contraseña acceda al siguiente link:

http://127.0.0.1:5000/restablecer_password?token_id={token_id}

Por favor, siga las instrucciones en la página para restablecer su contraseña.

Este es un correo automático, por favor no responda.
            """)

            # Enviar correo
            mail.send(msg) 

            conexion.connection.commit()

            return jsonify({"mensaje" : "email enviado con exito"}), 200
            
        else:
             return jsonify({"mensaje":"debe proporcionar un email"}), 400
        
    except Exception as e:
        return jsonify({"mensaje":"Error al enviar el correo", "error": {e}})



@app.route('/restablecer_password', methods=["POST"])
def restablecer_password():
    token_id = request.args.get('token_id')
    password = request.form.get('password')
  
    if not token_id or not password:
        return jsonify({"mensaje" : "formato de recuperación incorrecto"}), 400
    
    token_valido = verify_auth_token(token_id)
                
    if token_valido["status"] == "error":
        return jsonify (token_valido), 400
    
    # falta validar password
    
    try:   
        cursor = conexion.connection.cursor()

        usuario_id = token_valido["data"]["id_user"]

        hashed_password = hash_password(password) 

        #verificar si token fue usado
        cursor.execute("SELECT usado FROM recuperar_password WHERE usuario_id = %s", (usuario_id,))
        token_usado = cursor.fetchone()
        
        if token_usado[0] == 1:
             return jsonify({"mensaje" : "token expirado"}), 500
        
        #cambiar contraseña
        cursor.execute("UPDATE usuarios SET password = %s WHERE id = %s", (hashed_password, usuario_id))

        #marcar token como usado
        cursor.execute("UPDATE recuperar_password SET usado = %s WHERE usuario_id = %s", (1, usuario_id,))


        conexion.connection.commit()

        return jsonify({"mensaje" : "contraseña cambiada exitosamente"}), 200
    
    except Exception as e:
         return jsonify({"mensaje":"Error al restablecer la contraseña", "error": str(e)}), 500
    
# ------------  CRUD tabla proyectos ------------------
@app.route('/proyectos', methods=["POST"]) #terminado
@token_required
def proyecto(id_token, role_token):
    
    titulo = request.form.get('titulo')
    description = request.form.get('description')
    url_deploy = request.form.get('url_deploy')
    url_repository = request.form.get('url_repository')
    tecnologias = request.form.getlist('tecnologias[]')
    estado = request.form.get('estado')
    integrantes = request.form.getlist('integrantes[]')
    user_id_by_admin = request.form.get('id')
    
    # buscar usuario y asignar rol
    validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)
    if validated_user_id["id"] is None:
            return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
           
    id_user = validated_user_id["id"]    
    
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)

        validaciones = {}

        if titulo:   
            validaciones["titulo"] = (validar_alfanumerico, titulo, "titulo")# cambiar validacion a ya que no permite espacios
        else:
            return jsonify ({"mensaje": " el titulo es requerido"})

        if description:
            validaciones["description"] = (verificar_longitud_informacion, description, "description")

        if url_deploy:
            validaciones["url_deply"] = (validar_url, url_deploy, "url_deploy")

        if url_repository:
            validaciones["url_repository"] = (validar_url, url_repository, "url_repository")

        if tecnologias:
            validaciones["tecnologias"] = (validar_comma_en_list, tecnologias, "tecnologias")# no esta validando que no haya caracteres especiales

        if estado:
            validaciones["estado"] = (validar_alfanumerico, estado, "estado")# cambiar validacion a ya que no permite espacios


        resultado_validacion = validar_datos_generica(cursor, validaciones)        
        if resultado_validacion: #llamarla not_validated o algo asi
            return jsonify(resultado_validacion), 400

        #insertar en tabla proyectos
        sql = """INSERT INTO proyectos(
                    titulo, 
                    descripcion, 
                    url_deploy, 
                    url_repository,
                    estado,
                    usuario_id_owner)
                    VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (titulo, description, url_deploy, url_repository, estado, id_user))
        
        #recuperar id de proyecto
        proyecto_id = cursor.lastrowid

        # insertar en tabla tecnologias_proyecto
        for tecnologia in tecnologias:
            cursor.execute("INSERT INTO tecnologias_proyecto (proyecto_id, tecnologia) VALUES (%s, %s)", (proyecto_id, tecnologia))
        
        # insertar en tabla usuarios_proyecto
        integrantes_id = [id_token]
        for email in integrantes:            
            usuario_id = find_user_by_email(cursor, email)#no estoy validando el formato del mail
            if usuario_id == None:
                return jsonify({"mensaje": f"el usuario {email} no se encuentra registrado", "error": "usuario invalido"})
            integrantes_id.append(usuario_id[0])
        
        for usuario_id in integrantes_id:
            cursor.execute("INSERT INTO usuarios_proyecto (usuario_id, proyecto_id) VALUES (%s, %s)", (usuario_id, proyecto_id))
        

        conexion.connection.commit()
        return jsonify({"mensaje": "proyecto cargado con exito"}),200      
    except Exception as ex: 
        conexion.connection.rollback()
        return jsonify({"mensaje": "Error al cargar el proyecto", "error": str(ex)}), 500    
    finally:
        cursor.close()



@app.route('/proyectos', methods=["GET"]) #terminado
def mostrar_proyecto():
    titulo = request.args.get('titulo')
    print(titulo)
    try:
        cursor=conexion.connection.cursor()
        sql= """
        SELECT
            p.titulo,
            p.descripcion,
            p.url_deploy,
            p.url_repository,
            p.estado,
            p.usuario_id_owner,
            GROUP_CONCAT(DISTINCT up.usuario_id SEPARATOR ',') AS creadores,
            GROUP_CONCAT(DISTINCT tp.tecnologia SEPARATOR ',') AS tecnologias
        FROM 
            proyectos p
        LEFT JOIN
            usuarios_proyecto up ON p.id = up.proyecto_id
        LEFT JOIN
            tecnologias_proyecto tp ON p.id = tp.proyecto_id
        WHERE 
            1 = 1       
            """
        parametros = []
        if titulo:
            sql += "AND titulo = %s"
            parametros.append(titulo)
        
        sql +=  "GROUP BY p.id"

        cursor.execute(sql, parametros)
        datos = cursor.fetchall()
        if datos:
            proyectos = {}
            for dato in datos:
                proyectos[dato[0]] = { "titulo" : dato[0],
                            "descripcion" : dato[1],
                            "url_deploy" : dato[2],
                            "url_repository" : dato[3],
                            "estado" : dato[4],
                            "usuario_id_owner" : dato[5],
                            "creadores_id" : dato[6],
                            "tecnologias" : dato[7]
                }

                for creador in proyectos["creadores"]:
                    print("buscar nombre y apellido por id")
                    
            return jsonify({"proyectos" : proyectos})
        else:
            return jsonify({"mensaje": "proyecto no encontrado"}), 404
    
    except Exception as ex:         
        return jsonify({"mensaje": "Error al buscar el proyecto", "error": str(ex)}), 500    
    finally:
        cursor.close()

        
# Endponit para modificar info de proyectos
# PUT --> moficiar proyecto

# Endponit para eliminar proyecto
# PUT --> eliminar proyecto
    #intentar hacer que elimine las relaciones de proyectos_usuarios a ese proyecto

# ------------  CRUD tabla proyectos_usuarios ------------------
# Endponit para modificar info de proyectos_usuarios (Serviria para agrerar un nuevo participante a un proyecto existente)
# POST --> agregar nuevo usuario a proyecto_usuario

# Endponit para eliminar info de proyectos_usuarios
# PUT --> eliminar usuario de proyecto_usuario


#consultas:
#en tabla proyectos:
# 1- Como hacer para que no haya proyectos duplicados? por nombre, por url deploy, por url_github?
# 2- Quien puede modificar o borrar un proyecto? el creador del proyecto o todos los participantes?

#en tabla usuarios_proyectos ( la tabla que indica que usuarios participaron en cada proyecto). Cuando un usuario crea un proyecto nuevo, en la tabla proyectos_usuarios se vincula a este usuario y todos los participantes al proyecto.
# 3- Quien puede agregar o quitar un participante? el que creo el proyecto o todos los usuarios que son participantes del proyecto?






# otra manera de enviar mails
    # try:
    # # Conexión al servidor SMTP
    #     with smtplib.SMTP('smtp.gmail.com', 587) as server:
    #         server.starttls()  # Iniciar TLS
    #         server.login('federico.tasso.musica@gmail.com', 'hysx xdrp ignc iqgq')
    #         server.sendmail('federico.tasso.musica@gmail.com', 'fedtasso@gmail.com', msg.as_string())
    #         print("Correo enviado exitosamente")
    #         return jsonify({'exito': "exito"}), 500
    # except Exception as e:
    #     print(f"Error: {e}")
    #     return jsonify ({f"error: {e}"})



# @app.route('/recuperar_password', methods=["PUT"])
# def recuperar_password():
#     password = request.form.get("password")
    
#     try:
#         cursor = conexion.connection.cursor()
               
#         if password:

#             #falta validar password
         
#             #seleccionas pass de bbdd
#             cursor.execute("SELECT password FROM usuarios WHERE id = %s", (id_user,))
#             password_bbdd = cursor.fetchone()
            
#             #verficar que el password sea distinto al almacenado
#             if verify_password(password_bbdd[0], password):
#                 return jsonify ({"mensaje": "la contraseña es identica a la actual"}), 400
#             #actualizar password
#             else:
#                 hashed_password = hash_password(password)                
#                 cursor.execute("UPDATE usuarios SET password = %s where id = %s", (hashed_password, id_token))
#                 conexion.connection.commit()
#                 return jsonify ({"mensaje": "contraseña actualizada con exito"}), 200
            
#     except Exception as ex:
#         return jsonify({"mensaje":"error al actualizar la contraseña", "error": str(ex)}), 500
    
#     finally:
#         cursor.close()

# @app.route('/actualizar_password', methods=["PUT"])
# def actualizar_password():
#     #recibir password request
#     password = request.form.get('password', None)
    
#     if token in request: (el token tiene el id y el mail y dura 15 min)
#         @token_required    
#         def funcion():

            
            
#             Hacer hash de contraseña
#             if password:
#                 hashed_password = hash_password(password)
            
#             actualizar pass

#             #      
            
            
            # recibir mail en request

            # verificar mail en bbdd

            # enviar mail con link. En el link enviar:
            #     actualizar_password?=token...
            







# # ------- Update tabla informacion sin imagen (JSON)    -----------

# @app.route('/informacion', methods=["PUT"])
# @token_required
# def actualizar_informacion(id_token, role_token):
#     datos= request.get_json()
#     informacion_adicional = datos.get('informacion_adicional')   
#     user_id_by_admin = datos.get('id')      
#     try: 
#         cursor=conexion.connection.cursor()
#         conexion.connection.autocommit(False)
        
#         #seleccionar id desde email
#         cursor.execute("SELECT id FROM usuarios WHERE id = %s",(id_token,))
#         id_user_bbdd = cursor.fetchone()     
        
#         #validar entradas
#         validaciones = {}

#         if informacion_adicional:
#             validaciones["informacion_adicional"] = (verificar_longitud_informacion, informacion_adicional, "informacion_adicional")
        
#         resultado_validacion = validar_datos_generica(cursor, validaciones)        
#         if resultado_validacion:
#             return jsonify(resultado_validacion), 400
        
#         # verificar rol de usuario
#         validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)

#         if validated_user_id["id"] is None:
#              return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
#         else:
#             id_user = validated_user_id["id"]
        
              
#         #actualizar informacion        
#         cursor.execute("SELECT count(*) FROM informacion WHERE usuario_id = %s", (id,))
#         existe_informacion = cursor.fetchone()[0]        
#         if existe_informacion:        
#             sql = """UPDATE 
#                         informacion 
#                     SET 
#                         informacion_adicional = %s                         
#                     WHERE 
#                         usuario_id = %s"""
#             cursor.execute(sql, (informacion_adicional, id_user))   
#         else:            
#             sql = """INSERT INTO
#                         informacion (usuario_id, informacion_adicional)
#                     VALUES 
#                         (%s,%s,%s)"""
#             cursor.execute(sql, (id_user, informacion_adicional))
                 
#         conexion.connection.commit()
#         return jsonify({"mensaje": "Datos actualizados"}), 200
#     except Exception as ex:        
#         conexion.connection.rollback()
#         return jsonify({"mensaje": "Error al registrar el usuario", "error": str(ex)}), 500
#     finally:
#         cursor.close()


# @app.route('/informacion', methods=["DELETE"])
# @token_required
# def borrar_informacion():
#     email = request.args.get('email')
#     try:
#         cursor=conexion.connection.cursor()
#         # seleccionar id desde email
#         cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
#         result = cursor.fetchone()
#         # comprobar si existe        
#         if result is None:
#             return jsonify ({"mensaje": "Informacion de usuario no encontrado"}), 404
#         # borrar informacion
#         id = result[0]
#         # comprobar si existe información asociada al usuario
#         cursor.execute("SELECT id FROM informacion WHERE usuario_id = %s", (id,))
#         informacion_result = cursor.fetchone()
#         if informacion_result is None:
#             return jsonify({"mensaje": "Informacion de usuario no encontrado"}), 404
#         #Borrar informacion de usuario
#         sql = "DELETE FROM informacion WHERE usuario_id = %s"
#         cursor.execute(sql,(id,))
#         conexion.connection.commit()
#         return jsonify({"mensaje":"Has eliminado la informacion del usuario"}), 200
#     except Exception as ex:
#         return jsonify({"mensaje":"error al eliminar la informacion", "error": str(ex)}), 500
#     finally:
#         cursor.close()

# # ------- Update Delete tabla perfiles    -----------

# @app.route('/perfiles', methods=["PUT"])
# @token_required
# def actualizar_perfiles():
#     email = request.args.get('email')
#     perfiles_request = request.args.getlist('perfiles')
#     try:
#         cursor = conexion.connection.cursor()
#         conexion.connection.autocommit(False)
#         #seleccionar id desde email
#         cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
#         result = cursor.fetchone()
#         #comprobar si existe
#         if result is None:
#             return jsonify ({"mensaje": "Usuario no encontrado"}), 404
#         id = result[0]        
#         #comprobar si nuevos perfiles estan en BBDD  e insertar
#         cursor.execute("SELECT perfil FROM perfiles WHERE usuario_id = %s", (id,))
#         perfiles_bbdd = [perfil[0] for perfil in cursor.fetchall()]
#         for perfil in perfiles_request:
#             if perfil not in perfiles_bbdd:
#                 sql = """
#                     INSERT INTO
#                         perfiles (usuario_id, perfil)
#                     VALUES
#                         (%s, %s)                                                       
#                 """
#                 cursor.execute(sql,(id, perfil))      
#         #comprobar si un perfil no estan en BBDD y borrar
#         for perfil in perfiles_bbdd:
#             if perfil not in perfiles_request:
#                 sql = """
#                     DELETE FROM
#                         perfiles 
#                     WHERE 
#                         usuario_id = %s  AND perfil = %s                                                     
#                 """
#                 cursor.execute(sql,(id, perfil))
#         conexion.connection.commit()                
#         return jsonify({"mensaje":"Perfiles actualizados correctamente"}), 200
#     except Exception as ex:        
#         conexion.connection.rollback()
#         return jsonify ({"mensaje": "error al actualizar el perfil", "error": str(ex)}), 500
#     finally:
#         cursor.close()



# @app.route('/perfiles', methods=["DELETE"])
# @token_required
# def borrar_perfiles():
#     email = request.args.get('email')
#     perfiles = request.args.getlist("perfiles")    
#     try:
#         cursor = conexion.connection.cursor()
#         # seleccionar id desde email
#         cursor.execute("SELECT id FROM usuarios WHERE email = %s",(email,))
#         result = cursor.fetchone()
#         # comprobar si existe
#         if result is None:
#             return jsonify ({"mensaje":"usuario no encontrado"}),404                
#         id = result [0]
#         # comprobar si existe información asociada al usuario
#         cursor.execute("SELECT id FROM perfiles WHERE usuario_id = %s", (id,))
#         informacion_result = cursor.fetchone()        
#         if informacion_result is None:
#             return jsonify({"mensaje": "Informacion de usuario no encontrado"}), 404
#         #borrar todos los perfiles si no viene lista en request perfiles
#         if not perfiles:
#             cursor.execute("DELETE FROM perfiles WHERE usuario_id = %s", (id,))
#             conexion.connection.commit()
#             return jsonify({"mensaje":"Has eliminado los perfiles del usuario"}) 
#         #borrar los perfiles de la lista request perfiles
#         else:            
#             for perfil in perfiles:
#                 cursor.execute("DELETE FROM perfiles WHERE usuario_id = %s AND perfil = %s", (id, perfil))
#             conexion.connection.commit()
#             return jsonify({"mensaje":"Has eliminado el perfil del usuario"})
#     except Exception as ex:
#         return jsonify ({"mensaje":"error al eliminar el perfil", "error": str(ex)}), 500
#     finally:
#         cursor.close()



# ------- Update Delete tabla tecnologias   -----------

# @app.route('/tecnologias', methods=["PUT"])
# @token_required
# def actualizar_tecnologias():
#     email = request.args.get('email')
#     tecnologias_request = request.get_json() 
#     try:
#         cursor = conexion.connection.cursor()
#         conexion.connection.autocommit(False)
#         # seleccionar id desde email
#         cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
#         result = cursor.fetchone()
#         #comprobar si existe
#         if result is None:
#             return jsonify ({"mensaje":"usuario no encontrado"}), 404
#         id = result[0]
#         # comprobar si los tecnologias exiten en la bbdd
#         cursor.execute("SELECT tecnologia, nivel FROM tecnologias WHERE usuario_id = %s", (id,))
#         tecnologia_bbdd_dic = {clave: valor for clave, valor in cursor.fetchall()}
#         for tecnologia, nivel in tecnologias_request.items():
#             if tecnologia in tecnologia_bbdd_dic:
#                 # Actualiar si el tecnologia ya existe y el nivel es diferente
#                 if nivel != tecnologia_bbdd_dic[tecnologia]:
#                     cursor.execute("UPDATE tecnologias SET nivel = %s WHERE usuario_id = %s AND tecnologia = %s", (nivel, id, tecnologia ))
#             else:
#                 #insertar si el tecnologia no existe
#                 sql = ("""
#                         INSERT INTO
#                             tecnologias (usuario_id, tecnologia, nivel)
#                         VALUES
#                             (%s, %s, %s)
#                     """)                
#                 cursor.execute(sql, (id, tecnologia, nivel))
#         for tecnologia in tecnologia_bbdd_dic:
#             if tecnologia not in tecnologias_request:
#                 cursor.execute("DELETE FROM tecnologias WHERE usuario_id = %s AND tecnologia = %s ", (id, tecnologia))        
#         conexion.connection.commit()
#         return jsonify({"mensaje":"Has actualizado los tecnologias del usuario"})
#     except Exception as ex:
#         return jsonify({"mensaje":"error al actualizar los tecnologias del usuario", "error": str(ex)}), 500
#     finally:
#         cursor.close()



# @app.route('/tecnologias', methods=["DELETE"])
# @token_required
# def borrar_tecnologias():
#     email = request.args.get('email')
#     tecnologias = request.args.getlist("tecnologias")     
#     try:
#         cursor = conexion.connection.cursor()
#         # seleccionar id desde email
#         cursor.execute("SELECT id FROM usuarios WHERE email = %s",(email,))
#         result = cursor.fetchone()
#         # comprobar si existe
#         if result is None:
#             return jsonify ({"mensaje":"usuario no encontrado"}),404
                
#         id = result [0]
#          # comprobar si existe información asociada al usuario
#         cursor.execute("SELECT id FROM informacion WHERE usuario_id = %s", (id,)) 
#         informacion_result = cursor.fetchone()
#         if informacion_result is None:
#             return jsonify({"mensaje": "Informacion de usuario no encontrado"}), 404
#         #borrar todos los tecnologias si no viene lista en request perfiles
#         if not tecnologias:
#             cursor.execute("DELETE FROM tecnologias WHERE usuario_id = %s", (id,))
#             conexion.connection.commit()
#             return jsonify({"mensaje":"Has eliminado todos las tecnologias del usuario"}) 
#         #borrar los tecnologias de la lista request perfiles
#         else:            
#             for tecnologia in tecnologias:
#                 cursor.execute("DELETE FROM tecnologias WHERE usuario_id = %s AND tecnologia = %s", (id, tecnologia))
#             conexion.connection.commit()
#             return jsonify({"mensaje":"Has eliminado el los tecnologias del usuario"})
#     except Exception as ex:
#         return jsonify ({"mensaje":"error al eliminar el perfil", "error": str(ex)}), 500
#     finally:
#         cursor.close()



def pagina_no_encontrada(error):
    return "<h1>La página no existe</h1>",404

if __name__=='__main__':
    app.register_error_handler(404,pagina_no_encontrada) 
    app.run()
    





#-------------------- BORRAR ------------------------------


# # ------- Update tablas --> usuarios, informacion, perfiles, tecnologias -----------
# @app.route('/usuario', methods=["PUT"])
# @token_required
# def actualizar_usuario(id_token, role_token):
#     datos= request.get_json(silent=True)
#     if datos is None:
#         return jsonify({"mensaje": "No se ha enviado ninguna información"}), 400
    
#     nombre = datos.get('nombre')
#     apellido = datos.get('apellido')
#     email = datos.get('email')    
#     info_adicional = datos.get('info_adicional')
#     image = datos.get('image')
#     perfiles = datos.get('perfiles')
#     tecnologias = datos.get('tecnologias')
#     user_id_by_admin = datos.get('id')
  
#     try: 
#         cursor=conexion.connection.cursor()      
#         conexion.connection.autocommit(False)

#         #verificar rol        
#         validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)

#         if validated_user_id["id"] is None:
#              return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
#         else:
#             id_user = validated_user_id["id"]

#         #buscar informacion del usuario en la bbdd
#         info_user_front = {"nombre": nombre, 
#                           "apellido": apellido, 
#                           "email": email, 
#                           "info_adicional": info_adicional, 
#                           "image": image, 
#                           "perfiles": perfiles, 
#                           "tecnologias": tecnologias
#                             }      
               
#         cursor.execute("""
#                        SELECT u.nombre, u.apellido, u.email, i.informacion_adicional, i.image, 
#                        GROUP_CONCAT(DISTINCT p.perfil SEPARATOR ',') AS perfiles,
#                        GROUP_CONCAT(DISTINCT t.tecnologia SEPARATOR ',') AS tecnologias
#                        FROM usuarios u
#                        LEFT JOIN informacion i ON u.id = i.usuario_id
#                        LEFT JOIN perfiles p ON u.id = p.usuario_id
#                        LEFT JOIN tecnologias t ON u.id = t.usuario_id
#                        WHERE u.id = %s
#                        """, (id_user,))     
#         user_bbdd = cursor.fetchone()
      

#         info_user_bbdd = {"nombre":user_bbdd[0], 
#                           "apellido":user_bbdd[1], 
#                           "email":user_bbdd[2], 
#                           "info_adicional":user_bbdd[3], 
#                           "image":user_bbdd[4], 
#                           "perfiles":user_bbdd[5], 
#                           "tecnologias":user_bbdd[6]
#                             }
        
#         # verificar si la informacion es igual a la almacenada en BBDD  
#         verificar_con_bbdd = {}
       
#         for key, value in info_user_front.items():
#             if value:
#                 verificar_con_bbdd[key] = value
            
#         datos_actualizar = verificacion_con_bbdd(id_user, verificar_con_bbdd, info_user_bbdd)
        
#         if not datos_actualizar:
#             return jsonify ({"mensaje": "todos los datos ya existen"}), 400  
           
#         if "error" in datos_actualizar:
#             return jsonify(datos_actualizar), 500

         
#         #validar entradas
#         validaciones = {}

#         if "nombre" in datos_actualizar:
#             validaciones["nombre"] = (validar_alpha, datos.get('nombre'), "nombre")
    
#         if "apellido" in datos_actualizar:
#             validaciones["apellido"] = (validar_alpha, datos.get('apellido'), "apellido")
        
#         if "email" in datos_actualizar:
#             validaciones["email"] = (validar_y_verificar_email, datos.get('email'), "email", cursor)
        
#         if "perfiles" in datos_actualizar:
#             validaciones["perfiles"] = (validar_comma_en_list, datos.get('perfiles'), "perfiles")
        
#         if "tecnologias" in datos_actualizar:
#             validaciones["tecnologias"] = (validar_comma_en_list, datos.get('tecnologias'), "tecnologias")
                       
#         resultado_validacion = validar_datos_generica(cursor, id_user, validaciones)        
#         if resultado_validacion:
#             return jsonify(resultado_validacion), 400
      
#         # modificar datos de tabla usuarios
#         set_clause = {
#               "usuarios": [],
#               "informacion": [],
#               "perfiles" : [],
#               "tecnologias" : []
#         }
#         params = {
#               "usuarios": [],
#               "informacion": [],
#               "perfiles" : [],
#               "tecnologias" : [], 
#         }
        
    
#         if "nombre" in datos_actualizar:
#             set_clause["usuarios"].append("nombre = %s")
#             params["usuarios"].append(nombre)
        
#         if "apellido" in datos_actualizar:
#             set_clause["usuarios"].append("apellido = %s")
#             params["usuarios"].append(apellido)

#         if "email" in datos_actualizar:                        
#             set_clause["usuarios"].append("email = %s")
#             params["usuarios"].append(email)

#         if "info_adicional" in datos_actualizar:
#             set_clause["informacion"].append("informacion_adicional = %s")
#             params["informacion"].append(info_adicional)

#         if "image" in datos_actualizar:
#             set_clause["informacion"].append("image = %s")
#             params["informacion"].append(image)

   
#         # actualizar usuario
#         if set_clause["usuarios"]:
#             params["usuarios"].append(id_user)
#             sql = f"""UPDATE usuarios
#                             SET {', '.join(set_clause["usuarios"])} 
#                             WHERE id = %s"""
#             cursor.execute(sql, tuple(params["usuarios"]))

#         # actualizar informacion
#         if set_clause["informacion"]:
#             params["informacion"].append(id_user)
#             sql = f"""UPDATE informacion
#                             SET {', '.join(set_clause["informacion"])} 
#                             WHERE usuario_id = %s"""
#             cursor.execute(sql, tuple(params["informacion"]))

#         # actualizar perfiles
#         if "perfiles" in datos_actualizar:             
#             for value in datos_actualizar["perfiles"]["update"]:            
#                 sql = """
#                     INSERT INTO
#                         perfiles (usuario_id, perfil)
#                     VALUES
#                         (%s, %s)                                                       
#                 """                    
#                 cursor.execute(sql,(id_user, value))      
        
#         #borrar perfiles            
#             for value in datos_actualizar["perfiles"]["delete"]:                 
#                 sql = """
#                     DELETE FROM
#                         perfiles 
#                     WHERE 
#                         usuario_id = %s  AND perfil = %s                                                     
#                 """
#                 cursor.execute(sql,(id_user, value)) 

#          # actualizar tecnologias
#         if "tecnologias" in datos_actualizar:             
#             for value in datos_actualizar["tecnologias"]["update"]:            
#                 sql = """
#                     INSERT INTO
#                         tecnologias (usuario_id, tecnologia)
#                     VALUES
#                         (%s, %s)                                                       
#                 """                    
#                 cursor.execute(sql,(id_user, value))      
        
#         #borrar tecnologias            
#             for value in datos_actualizar["tecnologias"]["delete"]:                 
#                 sql = """
#                     DELETE FROM
#                         tecnologias 
#                     WHERE 
#                         usuario_id = %s  AND tecnologia = %s                                                     
#                 """
#                 cursor.execute(sql,(id_user, value)) 


#         conexion.connection.commit()
#         return jsonify({"mensaje": "Datos actualizados"}), 200        
#     except Exception as ex:        
#         conexion.connection.rollback()
#         return jsonify({"mensaje": "Error al actualizar el usuario", "error": str(ex)}), 500
#     finally:
#         cursor.close()
