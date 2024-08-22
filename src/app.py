from flask import Flask, jsonify, request
from flask_mysqldb import MySQL 
from security import hash_password, verify_password, generate_auth_token, verify_auth_token, token_required
from config import config

app=Flask(__name__)

conexion=MySQL(app)


# Hacer validaciones de datos entrantes
# Hacer hash de contraseña
# Considera retornar un código HTTP 409 Conflict en lugar de 200 si el usuario ya existe.

# ------- login -----------
@app.route('/login', methods=["POST"])
def login():
    datos=request.get_json()
    email = datos.get('email')
    user_pass_front = datos.get('password')
    try:
        cursor=conexion.connection.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = %s" , (email,))
        usuario = cursor.fetchone()
        if usuario is None:
             return jsonify({"mensaje":"El usuario no se encuentra registrado"}), 409
        user_pass_bbdd = usuario[4]
        if usuario and verify_password(user_pass_bbdd, user_pass_front):            
            token = generate_auth_token(usuario[0])
            return jsonify({'token': token,
                            "nombre" : usuario[1],
                            "apellido" : usuario[2],
                            "email" : usuario[3]
                            }), 200
        else:
            return jsonify({"mensaje": "Credenciales inválidas"}), 401  
    except Exception as ex:
        return jsonify({"mensaje": "Error al loguear el usuario", "error": str(ex)}), 500  
    finally:
        cursor.close()



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
        print(usuario)
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
                l.nivel
            FROM 
                usuarios u
            LEFT JOIN 
                informacion i ON u.id = i.usuario_id
            LEFT JOIN
                perfiles p ON u.id = p.usuario_id
            LEFT JOIN 
                lenguajes l ON u.id = l.usuario_id
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
        # ejecura consulta
        cursor.execute(sql, parametros)
        datos=cursor.fetchall()
        if datos:
            usuarios_dict = {}        
            for user in datos:
                user_id = user[0]            
                if user_id not in usuarios_dict:
                    usuarios_dict[user_id] = {
                        "id": user_id,
                        "nombre": user[1],
                        "apellido": user[2],
                        "email": user[3],
                        # "contraseña": user[4],
                        "informacion": user[5],
                        "image": user[6],
                        "perfiles": [], 
                        "lenguaje_nivel": {}
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
        print(ex)
        return jsonify({"mensaje": "Error al buscar datos del usuario", "error": str(ex)}), 500
    
    finally:
        cursor.close()


@app.route('/usuario', methods=["DELETE"])
@token_required
def borrar_usuario():
    email = request.args.get('email')
    try:
        cursor=conexion.connection.cursor()
        #seleccionar id desde email
        cursor.execute(("SELECT id FROM usuarios WHERE email = %s"),(email,))
        result = cursor.fetchone()
        #comprobar si existe
        if result is None:
            return jsonify({"mensaje": "Usuario no encontrado"}), 404
        id= result[0]  
        #Borrar usuario
        sql = "DELETE FROM usuarios WHERE id = %s"
        cursor.execute(sql,(id,))
        conexion.connection.commit()
        return jsonify({"mensaje":"Has eliminado el usuario"}), 200
    except Exception as ex:
        print(ex)
        return jsonify({"mensaje":"error al eliminar el usuario", "error": str(ex)}), 500
    finally:
        cursor.close()



# ------- Update tabla usuarios -----------

@app.route('/usuario', methods=["PUT"])
@token_required
def actualizar_usuario():
    email = request.args.get('email')
    datos= request.get_json()
    nombre = datos.get('nombre')  # Hacer que se pueda cambiar solo una vez por mes
    apellido = datos.get('apellido')
    password = datos.get('password')  #Hacer esta actualizacion en una peticion separada por seguridad
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)
        #seleccionar id desde email
        cursor.execute("SELECT id FROM usuarios WHERE email = %s",(email,))
        result = cursor.fetchone()
        #comprobar si existe
        if result is None:
            return jsonify ({"mensaje": "Usuario no encontrado"}), 404
        # Hacer hash de contraseña
        hashed_password = hash_password(password)
        # actualizar usuario
        id = result[0]
        sql = """UPDATE
                    usuarios 
                SET 
                    nombre=%s, 
                    apellido=%s, 
                    password=%s 
                WHERE 
                    id = %s"""
        cursor.execute(sql, (nombre, apellido, hashed_password, id))
        conexion.connection.commit()
        return jsonify({"mensaje": "Datos actualizados"}), 200    
    except Exception as ex:        
        conexion.connection.rollback()
        return jsonify({"mensaje": "Error al actualizar el usuario", "error": str(ex)}), 500
    finally:
        cursor.close()


# ------- Update Delete tabla informacion    -----------

@app.route('/informacion', methods=["PUT"])
@token_required
def actualizar_informacion():
    email = request.args.get('email') 
    datos= request.get_json()
    informacion = datos.get('informacion_adicional')
    image = datos.get('image')    
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)
        #seleccionar id desde email
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        result = cursor.fetchone()
        #comprobar si existe
        if result is None:
            return jsonify ({"mensaje": "Usuario no encontrado"}), 404
        #actualizar informacion
        id = result[0]
        cursor.execute("SELECT count(*) FROM informacion WHERE usuario_id = %s", (id,))
        existe_informacion = cursor.fetchone()[0]
        print(existe_informacion)       
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
        print(informacion_result)
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
    print(f"Email recibido: {email}")
    print(f"Lenguajes recibidos: {lenguajes}")    
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
    