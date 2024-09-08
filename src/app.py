from flask import Flask, jsonify, request
from flask_mysqldb import MySQL 
from security import hash_password, verify_password, generate_auth_token, verify_auth_token, token_required, admin_can_modify
from config import config

app=Flask(__name__)

conexion=MySQL(app)


# Hacer validaciones de datos entrantes
# Hacer hash de contraseña
# Considera retornar un código HTTP 409 Conflict en lugar de 200 si el usuario ya existe.
# endponit de admin para crear
# contraseña en otro endponit
# terminar de corregir codigo 
# hacer todas las pruebas

###################### PASAR A OTRO ARCHIVO ##################

import re

def find_user_by_id(cursor, user_id):
    cursor.execute("SELECT id FROM usuarios WHERE id = %s", (user_id,))
    return cursor.fetchone()

def role_find_and_validate(user_id_by_admin, id_token, role_token):
    try:
        cursor=conexion.connection.cursor()

        #permisos de administrador
        if role_token == 1:            
            
            if user_id_by_admin > 1 or not isinstance(user_id_by_admin, int):
                return {"id" : None, "mensaje" : "Debe proporcionar un id valido"}
            
            if user_id_by_admin == None:
                user_id = id_token
                return {"id" : user_id}
            else:
                user_id = user_id_by_admin
                user_id_bbdd = find_user_by_id(cursor, user_id)
                if user_id_bbdd is None:
                    return {"id" : None, "mensaje" : "Usuario no encontrado"}
                else:                
                    return {"id" : user_id}
        
        #permisos de usuario
        else:
            user_id_bbdd = find_user_by_id(cursor, id_token)
            
            if user_id_bbdd is None:
                return {"id" : None, "mensaje" : "Usuario no encontrado"}
            else:
                return {"id" : id_token} 
            
    except Exception as ex:
        conexion.connection.rollback()
        raise ex    
    finally:
        cursor.close()


def validar_datos_generica(cursor, id_user, validaciones):
    for campo, (funcion, *args) in validaciones.items():
        if args[0] is None:  # Si el valor es None, no validar
            continue

        error_al_validar = funcion(args[0],args[1])
        
        if error_al_validar:
            return error_al_validar
    return None


def validar_alpha(dato_usuario, campo_bbdd):
    if not dato_usuario.isalpha():
        dato_invalido = {"mensaje": f" El {campo_bbdd} no cumple con el formato establecido", 
                         "dato_invalido" : campo_bbdd}
        return dato_invalido
    return None


def validar_alfanumerico(dato_usuario, campo_bbdd):
    if not dato_usuario.isalnum():
        dato_invalido = {"mensaje": f" El {campo_bbdd} no cumple con el formato establecido", 
                         "dato_invalido" : campo_bbdd}
        return dato_invalido
    return None


def validar_email(email, campo_bbdd):    
    patron = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(patron, email):
        dato_invalido = {"mensaje": f" El {campo_bbdd} no cumple con el formato establecido", 
                         "dato_invalido" : campo_bbdd}
        return dato_invalido
    return None
        

def verificar_con_bbdd(cursor, id_user, verificaciones):    
    try:

        datos_distintos = []
        
        for key, value in verificaciones.items():
            dato_usuario = value[0]
            campo_bbdd = value[1]
            tabla = value[2]
            
            cursor.execute(f"SELECT {campo_bbdd} FROM {tabla} WHERE id = %s", (id_user,))
            resultado_bbdd = cursor.fetchone()                     
             
            if dato_usuario != resultado_bbdd[0]:
                datos_distintos.append(key)     

        if datos_distintos:
            return datos_distintos
                
    except Exception as ex:       
        return {"mensaje": "Error al actualizar el usuario", "error": str(ex)}
   

    

# ------- CREAR ENDPOINT PARA user admin si id no existe -----------







############################################Falta Validar#############################
# ------- login -----------
@app.route('/login', methods=["POST"])
def login():
    datos = request.get_json()
    email = datos.get('email')
    user_pass_front = datos.get('password')
    try:
        cursor = conexion.connection.cursor()
        sql = """SELECT 
                    u.id, 
                    u.nombre,
                    u.apellido, 
                    u.password,
                    ru.rol_id 
                FROM 
                    usuarios u
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
            rol = usuario[4]
            token = "Bearer " + generate_auth_token(id_user, rol)
            return jsonify({'token': token,
                            "nombre" : usuario[1],
                            "apellido" : usuario[2]                            
                            }), 200
        else:
            return jsonify({"mensaje": "Credenciales inválidas"}), 401  
    except Exception as ex:
        return jsonify({"mensaje": "Error al loguear el usuario", "error": str(ex)}), 500  
    finally:
        cursor.close()

############################################Falta Validar#############################

# ------- CRUD usuario -----------

@app.route('/registrar', methods=["POST"]) 
def registrar():
    datos= request.get_json()
    nombre = datos.get('nombre') 
    apellido = datos.get('apellido')
    email = datos.get('email')
    password = datos.get('password')
    informacion_adicional = datos.get('informacion_adicional')
    image = datos.get('image') #cursor de tiempo para que baje en tiempo real
    perfiles = datos.get('perfiles')
    lenguajes = datos.get('lenguajes')    
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)
        #Verificar si el usuario existe
        cursor.execute("SELECT email FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()
        if usuario is not None:
            return jsonify({"mensaje":"El usuario ya se encuentra registrado"}), 409 
        # Hacer hash de contraseña
        hashed_password = hash_password(password)
        # Insertar en tabla usuarios
        sql = "INSERT INTO usuarios (nombre, apellido, email, password) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nombre, apellido, email, hashed_password))
        usuario_id = cursor.lastrowid
        # insertar en tabla informacion (me aseguro que usuario e informacion tengan el mismo id)
        sql = "INSERT INTO informacion (usuario_id, informacion_adicional, image) VALUES (%s, %s, %s)"
        cursor.execute(sql, (usuario_id,informacion_adicional,image))
        # insetar en tabla perfiles
        for perfil in perfiles:
            sql = "INSERT INTO perfiles (usuario_id, perfil) VALUES(%s, %s)"
            cursor.execute(sql,(usuario_id,perfil))
        #clave=lenguaje, valor=nivel
        for clave, valor in lenguajes.items():
            cursor.execute("INSERT INTO lenguajes (usuario_id, lenguaje, nivel) VALUES (%s, %s, %s)", (usuario_id, clave, valor))
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


# mostrar participantes
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
                u.password,
                i.informacion_adicional,
                i.image,
                p.perfil,
                l.lenguaje,
                l.nivel,
                ru.rol_id
            FROM 
                usuarios u
            LEFT JOIN 
                informacion i ON u.id = i.usuario_id
            LEFT JOIN
                perfiles p ON u.id = p.usuario_id
            LEFT JOIN 
                lenguajes l ON u.id = l.usuario_id
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
                if user[10] == 1:
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
                        "informacion": user[5],
                        "image": user[6],
                        "perfiles": [], 
                        "lenguaje_nivel": {},
                        "rol": rol
                }            
                if user[7] is not None and user[7] not in usuarios_dict[user_id]["perfiles"]:
                    usuarios_dict[user_id]["perfiles"].append(user[7])
                if user[8] is not None and user[8] not in usuarios_dict[user_id]["lenguaje_nivel"]:
                    usuarios_dict[user_id]["lenguaje_nivel"][user[8]] = user[9]         
            usuarios = list(usuarios_dict.values())       
            return jsonify({"usuarios":usuarios,"mensaje":"Todos los usuarios"}), 200
        else:
            return jsonify({"mensaje": "Usuario no encontrado"}), 404
    except Exception as ex:    
        return jsonify({"mensaje": "Error al buscar datos del usuario", "error": str(ex)}), 500    
    finally:
        cursor.close()

#Si admin envia id modifica el usuario indicado
#Si admin no envia id, modifica su propia informacion

# ------- Update tablas --> usuarios, informacion, perfiles, lenguajes -----------
@app.route('/usuario', methods=["PUT"])
@token_required
def actualizar_usuario(id_token, role_token):
    datos= request.get_json(silent=True)
    if datos is None:
        return jsonify({"mensaje": "No se ha enviado ninguna información"}), 400
    
    nombre = datos.get('nombre')
    apellido = datos.get('apellido')
    email = datos.get('email')
    password = datos.get('password') #pasar a otro endpoint
    informacion_adicional = datos.get('informacion_adicional')
    image = datos.get('image')
    perfiles = datos.get('perfiles')
    lenguajes = datos.get('lenguajes')

    user_id_by_admin = datos.get('id')
      
    try: 
        cursor=conexion.connection.cursor()      
        conexion.connection.autocommit(False)

        #verificar rol        
        validated_user_id = role_find_and_validate(user_id_by_admin, id_token, role_token)

        if validated_user_id["id"] is None:
             return jsonify ({"mensaje": validated_user_id["mensaje"]}), 404
        else:
            id_user = validated_user_id["id"]
       

        # verificar si la informacion es igual a la almacenada en BBDD
        verificacion_con_bbdd = {}

        if nombre:            
            verificacion_con_bbdd["nombre"] = (nombre, "nombre", "usuarios")
                   
        if apellido:
            verificacion_con_bbdd["apellido"] = (apellido, "apellido", "usuarios")

        if email:
            verificacion_con_bbdd["email"] = (email, "email", "usuarios")        
           
        resultado_verificacion = verificar_con_bbdd(cursor, id_user, verificacion_con_bbdd)

        if not resultado_verificacion:
            return jsonify ({"mensaje": "todos los datos ya existen"}), 400  
      
        if "error" in resultado_verificacion:
            return jsonify(resultado_verificacion), 500
     

        #validar entradas
        validaciones = {}

        if "nombre" in resultado_verificacion:
            validaciones["nombre"] = (validar_alpha, datos.get('nombre'), "nombre")
    
        if "apellido" in resultado_verificacion:
            validaciones["apellido"] = (validar_alpha, datos.get('apellido'), "apellido")
        
        if "email" in resultado_verificacion:
            validaciones["email"] = (validar_email, datos.get('email'), "email")
           
          
        resultado_validacion = validar_datos_generica(cursor, id_user, validaciones)
        if resultado_validacion:
            return jsonify(resultado_validacion), 400
        
        # modificar datos de tabla usuarios
        set_clause = []
        params = []
        
        if "nombre" in validaciones:
            set_clause.append("nombre = %s")
            params.append(nombre)
        
        if "apellido" in validaciones:
            set_clause.append("apellido = %s")
            params.append(apellido)

        if "email" in validaciones:
            set_clause.append("email = %s")
            params.append(email)

        params.append(validated_user_id["id"])
       
        if not set_clause:
            return jsonify({"mensaje": "No se proporcionaron campos para actualizar"}), 400
       
        # actualizar usuario        
        sql = f"""UPDATE
                    usuarios 
                SET 
                    {', '.join(set_clause)} 
                WHERE 
                    id = %s"""
        cursor.execute(sql, params)
        conexion.connection.commit()
        return jsonify({"mensaje": "Datos actualizados"}), 200        
    except Exception as ex:        
        conexion.connection.rollback()
        return jsonify({"mensaje": "Error al actualizar el usuario", "error": str(ex)}), 500
    finally:
        cursor.close()
@app.route('/usuario', methods=["DELETE"])
@token_required
def borrar_usuario(id_token, role_token):
    datos= request.get_json(silent=True)
    
    try:
        cursor=conexion.connection.cursor()

        #verificar si es admin        
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



# ------- CREAR ENDPOINT PARA CONTRASEÑA -----------

# password = datos.get('password', None)  #Hacer esta actualizacion en una peticion separada por seguridad
# Hacer hash de contraseña
        # if password:
        #     hashed_password = hash_password(password)


######### A OTRO ENDPOINT #############
# if password:
#     cursor.execute("SELECT password FROM usuarios WHERE id = %s", (id_token,))
#     user_pass_bbdd = cursor.fetchone()
#     if not verify_password(user_pass_bbdd[0], password):
            # "password": (validar_password, datos.get('password')),
#         hashed_password = hash_password(password)
#         cursor.execute("UPDATE usuarios SET password = %s where id = %s", (hashed_password, id_token))
#         conexion.connection.commit()
#         return jsonify ({"mensaje": "contraseña actualizada con exito"}), 200
#     else:
#         return jsonify ({"mensaje": "la contraseña es identica a la actual"}), 400



############################################CONTINUAR VALIDANDO Y VERIFICANDO DESDE ACA#############################

# ------- Update Delete tabla informacion    -----------

@app.route('/informacion', methods=["PUT"])
@token_required
def actualizar_informacion(id_token, role_token):
    datos= request.get_json()
    informacion = datos.get('informacion_adicional')
    image = datos.get('image')  
    id_user_admin = datos.get('id')      
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)
        
        #seleccionar id desde email
        cursor.execute("SELECT id FROM usuarios WHERE id = %s",(id_token,))
        id_user_bbdd = cursor.fetchone()     
        
        #comprobar si existe
        if id_user_bbdd is None:
            return jsonify ({"mensaje": "debe logearse"}), 401
        
        id = id_user_bbdd[0]
        
        #verificar si es admin        
        if admin_can_modify(role_token):                 
            id = id_user_admin
        
        #actualizar informacion        
        cursor.execute("SELECT count(*) FROM informacion WHERE usuario_id = %s", (id,))
        existe_informacion = cursor.fetchone()[0]        
        if existe_informacion:        
            sql = """UPDATE 
                        informacion 
                    SET 
                        informacion_adicional = %s, 
                        image = %s 
                    WHERE 
                        usuario_id = %s"""
            cursor.execute(sql, (informacion, image, id))   
        else:            
            sql = """INSERT INTO
                        informacion (usuario_id, informacion_adicional, image)
                    VALUES 
                        (%s,%s,%s)"""
            cursor.execute(sql, (id, informacion, image))
                 
        conexion.connection.commit()
        return jsonify({"mensaje": "Datos actualizados"}), 200
    except Exception as ex:        
        conexion.connection.rollback()
        return jsonify({"mensaje": "Error al registrar el usuario", "error": str(ex)}), 500
    finally:
        cursor.close()


@app.route('/informacion', methods=["DELETE"])
@token_required
def borrar_informacion():
    email = request.args.get('email')
    try:
        cursor=conexion.connection.cursor()
        # seleccionar id desde email
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        result = cursor.fetchone()
        # comprobar si existe        
        if result is None:
            return jsonify ({"mensaje": "Informacion de usuario no encontrado"}), 404
        # borrar informacion
        id = result[0]
        # comprobar si existe información asociada al usuario
        cursor.execute("SELECT id FROM informacion WHERE usuario_id = %s", (id,))
        informacion_result = cursor.fetchone()
        if informacion_result is None:
            return jsonify({"mensaje": "Informacion de usuario no encontrado"}), 404
        #Borrar informacion de usuario
        sql = "DELETE FROM informacion WHERE usuario_id = %s"
        cursor.execute(sql,(id,))
        conexion.connection.commit()
        return jsonify({"mensaje":"Has eliminado la informacion del usuario"}), 200
    except Exception as ex:
        return jsonify({"mensaje":"error al eliminar la informacion", "error": str(ex)}), 500
    finally:
        cursor.close()

# ------- Update Delete tabla perfiles    -----------

@app.route('/perfiles', methods=["PUT"])
@token_required
def actualizar_perfiles():
    email = request.args.get('email')
    perfiles_request = request.args.getlist('perfiles')
    try:
        cursor = conexion.connection.cursor()
        conexion.connection.autocommit(False)
        #seleccionar id desde email
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        result = cursor.fetchone()
        #comprobar si existe
        if result is None:
            return jsonify ({"mensaje": "Usuario no encontrado"}), 404
        id = result[0]        
        #comprobar si nuevos perfiles estan en BBDD  e insertar
        cursor.execute("SELECT perfil FROM perfiles WHERE usuario_id = %s", (id,))
        perfiles_bbdd = [perfil[0] for perfil in cursor.fetchall()]
        for perfil in perfiles_request:
            if perfil not in perfiles_bbdd:
                sql = """
                    INSERT INTO
                        perfiles (usuario_id, perfil)
                    VALUES
                        (%s, %s)                                                       
                """
                cursor.execute(sql,(id, perfil))      
        #comprobar si un perfil no estan en BBDD y borrar
        for perfil in perfiles_bbdd:
            if perfil not in perfiles_request:
                sql = """
                    DELETE FROM
                        perfiles 
                    WHERE 
                        usuario_id = %s  AND perfil = %s                                                     
                """
                cursor.execute(sql,(id, perfil))
        conexion.connection.commit()                
        return jsonify({"mensaje":"Perfiles actualizados correctamente"}), 200
    except Exception as ex:        
        conexion.connection.rollback()
        return jsonify ({"mensaje": "error al actualizar el perfil", "error": str(ex)}), 500
    finally:
        cursor.close()



@app.route('/perfiles', methods=["DELETE"])
@token_required
def borrar_perfiles():
    email = request.args.get('email')
    perfiles = request.args.getlist("perfiles")    
    try:
        cursor = conexion.connection.cursor()
        # seleccionar id desde email
        cursor.execute("SELECT id FROM usuarios WHERE email = %s",(email,))
        result = cursor.fetchone()
        # comprobar si existe
        if result is None:
            return jsonify ({"mensaje":"usuario no encontrado"}),404                
        id = result [0]
        # comprobar si existe información asociada al usuario
        cursor.execute("SELECT id FROM perfiles WHERE usuario_id = %s", (id,))
        informacion_result = cursor.fetchone()        
        if informacion_result is None:
            return jsonify({"mensaje": "Informacion de usuario no encontrado"}), 404
        #borrar todos los perfiles si no viene lista en request perfiles
        if not perfiles:
            cursor.execute("DELETE FROM perfiles WHERE usuario_id = %s", (id,))
            conexion.connection.commit()
            return jsonify({"mensaje":"Has eliminado los perfiles del usuario"}) 
        #borrar los perfiles de la lista request perfiles
        else:            
            for perfil in perfiles:
                cursor.execute("DELETE FROM perfiles WHERE usuario_id = %s AND perfil = %s", (id, perfil))
            conexion.connection.commit()
            return jsonify({"mensaje":"Has eliminado el perfil del usuario"})
    except Exception as ex:
        return jsonify ({"mensaje":"error al eliminar el perfil", "error": str(ex)}), 500
    finally:
        cursor.close()



# ------- Update Delete tabla lenguajes   -----------

@app.route('/lenguajes', methods=["PUT"])
@token_required
def actualizar_lenguajes():
    email = request.args.get('email')
    lenguajes_request = request.get_json() 
    try:
        cursor = conexion.connection.cursor()
        conexion.connection.autocommit(False)
        # seleccionar id desde email
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        result = cursor.fetchone()
        #comprobar si existe
        if result is None:
            return jsonify ({"mensaje":"usuario no encontrado"}), 404
        id = result[0]
        # comprobar si los lenguajes exiten en la bbdd
        cursor.execute("SELECT lenguaje, nivel FROM lenguajes WHERE usuario_id = %s", (id,))
        lenguaje_bbdd_dic = {clave: valor for clave, valor in cursor.fetchall()}
        for lenguaje, nivel in lenguajes_request.items():
            if lenguaje in lenguaje_bbdd_dic:
                # Actualiar si el lenguaje ya existe y el nivel es diferente
                if nivel != lenguaje_bbdd_dic[lenguaje]:
                    cursor.execute("UPDATE lenguajes SET nivel = %s WHERE usuario_id = %s AND lenguaje = %s", (nivel, id, lenguaje ))
            else:
                #insertar si el lenguaje no existe
                sql = ("""
                        INSERT INTO
                            lenguajes (usuario_id, lenguaje, nivel)
                        VALUES
                            (%s, %s, %s)
                    """)                
                cursor.execute(sql, (id, lenguaje, nivel))
        for lenguaje in lenguaje_bbdd_dic:
            if lenguaje not in lenguajes_request:
                cursor.execute("DELETE FROM lenguajes WHERE usuario_id = %s AND lenguaje = %s ", (id, lenguaje))        
        conexion.connection.commit()
        return jsonify({"mensaje":"Has actualizado los lenguajes del usuario"})
    except Exception as ex:
        return jsonify({"mensaje":"error al actualizar los lenguajes del usuario", "error": str(ex)}), 500
    finally:
        cursor.close()



@app.route('/lenguajes', methods=["DELETE"])
@token_required
def borrar_lenguajes():
    email = request.args.get('email')
    lenguajes = request.args.getlist("lenguajes")     
    try:
        cursor = conexion.connection.cursor()
        # seleccionar id desde email
        cursor.execute("SELECT id FROM usuarios WHERE email = %s",(email,))
        result = cursor.fetchone()
        # comprobar si existe
        if result is None:
            return jsonify ({"mensaje":"usuario no encontrado"}),404
                
        id = result [0]
         # comprobar si existe información asociada al usuario
        cursor.execute("SELECT id FROM informacion WHERE usuario_id = %s", (id,)) 
        informacion_result = cursor.fetchone()
        if informacion_result is None:
            return jsonify({"mensaje": "Informacion de usuario no encontrado"}), 404
        #borrar todos los lenguajes si no viene lista en request perfiles
        if not lenguajes:
            cursor.execute("DELETE FROM lenguajes WHERE usuario_id = %s", (id,))
            conexion.connection.commit()
            return jsonify({"mensaje":"Has eliminado todos los lenguajes del usuario"}) 
        #borrar los lenguajes de la lista request perfiles
        else:            
            for lenguaje in lenguajes:
                cursor.execute("DELETE FROM lenguajes WHERE usuario_id = %s AND lenguaje = %s", (id, lenguaje))
            conexion.connection.commit()
            return jsonify({"mensaje":"Has eliminado el los lenguajes del usuario"})
    except Exception as ex:
        return jsonify ({"mensaje":"error al eliminar el perfil", "error": str(ex)}), 500
    finally:
        cursor.close()



def pagina_no_encontrada(error):
    return "<h1>La página no existe</h1>",404

if __name__=='__main__':
    app.config.from_object(config["development"])
    app.register_error_handler(404,pagina_no_encontrada) 
    app.run()
    