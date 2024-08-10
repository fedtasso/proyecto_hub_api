from flask import Flask, jsonify, request
from flask_mysqldb import MySQL 

from config import config

app=Flask(__name__)

conexion=MySQL(app)


# faltan todas las validaciones en cada endpoint
# verificar si la peticion existe o no en la bbdd antes de ejecutarla

#agregar los status 400 500 etc


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
    #agregar lenguajes
    
    try: 
        cursor=conexion.connection.cursor()
        conexion.connection.autocommit(False)
        #Insertar en tabla usuarios
        sql = "INSERT INTO usuarios (nombre, apellido, email, password) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nombre, apellido, email, password))
        user_id = cursor.lastrowid
        #insertar en tabla informacion(me aseguro que usuario e informacion tengan el mismo id)
        sql = "INSERT INTO informacion (usuario, informacion_adicional, image) VALUES (%s, %s, %s)"
        cursor.execute(sql, (user_id,informacion_adicional,image))
        #insetar en tabla perfiles
        for perfil in perfiles:
            sql = "INSERT INTO perfiles (usuario, perfil) VALUES(%s, %s)"
            cursor.execute(sql,(user_id,perfil))
        conexion.connection.commit()
        return jsonify({"mensaje": "Usuario registrado"})
        
    except Exception as ex:     # mostrar mensaje segun el tipo de error
        print(f"Error: {ex}") 
        return jsonify({"mensaje": "Error al registrar el usuario"})
    
    finally:
        cursor.close()


# busqueda por participante --> nombre y/o apellido
@app.route('/usuario', methods=["GET"])
def usuario():
    nombre = request.args.get('nombre')
    apellido = request.args.get('apellido')
    print (nombre)
    print (apellido)

    try:
        cursor=conexion.connection.cursor()
        if nombre is not None and apellido is not None:
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
                informacion i ON u.id = i.usuario
            LEFT JOIN
                perfiles p ON u.id = p.usuario
            LEFT JOIN 
                lenguajes l ON u.id = l.usuario
            WHERE 
                nombre = %s AND apellido= %s"""
            cursor.execute(sql, (nombre,apellido))
            datos=cursor.fetchall()
            if datos is not None:
                usuario_dict = {}
                for user in datos:
                    user_id = user[0]
                    if user_id not in usuario_dict:
                        usuario_dict[user_id] = {
                            "id": user_id,
                            "nombre": user[1],
                            "apellido": user[2],
                            "email": user[3],
                            "contraseña": user[4],
                            "informacion": user[5],
                            "image": user[6],
                            "perfiles": [], 
                            "lenguaje": user[8],
                            "nivel": user[9]
                        }
                    if user[7] is not None:
                        usuario_dict[user_id]["perfiles"].append(user[7])        
                usuario = list(usuario_dict.values())       
                return jsonify({"usuario":usuario,"mensaje": "Datos del usuario"})
            else:
                return jsonify({"mensaje": "Usuario no encontrado"})    
        else:
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
                informacion i ON u.id = i.usuario
            LEFT JOIN
                perfiles p ON u.id = p.usuario
            LEFT JOIN 
                lenguajes l ON u.id = l.usuario
            WHERE 
                nombre = %s OR apellido= %s"""
            cursor.execute(sql, (nombre,apellido))
            datos=cursor.fetchall()

            if datos is not None:
                usuario_dict = {}
                for user in datos:
                    user_id = user[0]
                    if user_id not in usuario_dict:
                        usuario_dict[user_id] = {
                            "id": user_id,
                            "nombre": user[1],
                            "apellido": user[2],
                            "email": user[3],
                            "contraseña": user[4],
                            "informacion": user[5],
                            "image": user[6],
                            "perfiles": [], 
                            "lenguaje": user[8],
                            "nivel": user[9]
                        }
                    if user[7] is not None:
                        usuario_dict[user_id]["perfiles"].append(user[7])
                usuario = list(usuario_dict.values())
                return jsonify({"usuarios":usuario,"mensaje":"Todos los usuarios"})
            else:
                return jsonify({"mensaje": "Usuario no encontrado"})        
    except Exception as ex:    
        print(ex)
        return jsonify({"mensaje": "Error al buscar datos del usuario"})    
    finally:
        cursor.close()


# mostrar todos los participantes
@app.route('/usuarios_todos', methods=["GET"]) 
def mostrar_todos_usuarios():
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
                informacion i ON u.id = i.usuario
            LEFT JOIN
                perfiles p ON u.id = p.usuario
            LEFT JOIN 
                lenguajes l ON u.id = l.usuario"""
        cursor.execute(sql)
        datos=cursor.fetchall()
        if datos is not None:
            usuarios_dict = {}        
            for user in datos:
                user_id = user[0]            
                if user_id not in usuarios_dict:
                    usuarios_dict[user_id] = {
                        "id": user_id,
                        "nombre": user[1],
                        "apellido": user[2],
                        "email": user[3],
                        "contraseña": user[4],
                        "informacion": user[5],
                        "image": user[6],
                        "perfiles": [], 
                        "lenguaje": user[8],
                        "nivel": user[9]
                    }            
                if user[7] is not None:
                    usuarios_dict[user_id]["perfiles"].append(user[7])        
            usuarios = list(usuarios_dict.values())       
            return jsonify({"usuarios":usuarios,"mensaje":"Todos los usuarios"})  
        else:
            return jsonify({"mensaje": "Usuario no encontrado"})        
    except Exception as ex:    
        print(ex)
        return jsonify({"mensaje": "Error al buscar datos del usuario"})  
    
    finally:
        cursor.close()


@app.route('/usuario', methods=["DELETE"])
def borrar_usuario():
    id = request.args.get('id')
    try:
        cursor=conexion.connection.cursor()
        sql = "DELETE FROM usuarios WHERE id=%s"
        cursor.execute(sql,(id,))
        conexion.connection.commit()
        return jsonify({"mensaje":"Has eliminado el usuario"})
    except Exception as ex:
        print(ex)
        return jsonify({"mensaje":"error al eliminar el usuario"})
    finally:
        cursor.close()



# ------- Update tabla usuarios -----------

@app.route('/usuario', methods=["PUT"])
def actualizar_usuario():
    id = request.args.get('id')
    datos= request.get_json()
    nombre = datos.get('nombre')  # Hacer que se pueda cambiar solo una vez por mes
    apellido = datos.get('apellido')
    email = datos.get('email')
    password = datos.get('password')  #Hacer esta actualizacion en una peticion separada por seguridad
    try: 
        cursor=conexion.connection.cursor()
        sql = """UPDATE
                    usuarios 
                SET 
                    nombre=%s, 
                    apellido=%s, 
                    email=%s, 
                    password=%s 
                WHERE 
                    id=%s"""
        cursor.execute(sql, (nombre, apellido, email, password, id))
        conexion.connection.commit()
        return jsonify({"mensaje": "Datos actualizados"})        
    except Exception as ex:
        print(f"Error: {ex}") 
        return jsonify({"mensaje": "Error al registrar el usuario"}), 500    
    finally:
        cursor.close()


# ------- Update Delete tabla informacion    -----------

@app.route('/informacion', methods=["PUT"])
def actualizar_informacion():
    id = request.args.get('id')  # me envia email, busco email en base de datos para traer id y hago peticion con id
    datos= request.get_json()
    informacion = datos.get('informacion_adicional')
    image = datos.get('image')    
    try: 
        cursor=conexion.connection.cursor()

        cursor.execute("SELECT count(*) FROM informacion WHERE usuario=%s", (id,))
        existe_informacion = cursor.fetchone()[0]
        print(existe_informacion)
        
        if existe_informacion:
            sql = """UPDATE 
                        informacion 
                    SET 
                        informacion_adicional=%s, 
                        image=%s 
                    WHERE 
                        id=%s"""
            cursor.execute(sql, (informacion, image, id))
            # return jsonify({"mensaje": "Datos actualizados"})        
        else:
            sql = """INSERT INTO
                        informacion (usuario, informacion_adicional, image)
                    VALUES 
                        (%s,%s,%s)"""
            cursor.execute(sql, (id, informacion, image))
                 
        conexion.connection.commit()
        return jsonify({"mensaje": "Datos actualizados"})
    except Exception as ex:
        print(f"Error: {ex}") 
        return jsonify({"mensaje": "Error al registrar el usuario"}), 500    
    finally:
        cursor.close()


@app.route('/informacion', methods=["DELETE"])
def borrar_informacion():
    id = request.args.get('id')
    try:
        cursor=conexion.connection.cursor()
        sql = "DELETE FROM informacion WHERE usuario = %s"
        cursor.execute(sql,(id,))
        conexion.connection.commit()
        return jsonify({"mensaje":"Has eliminado el usuario"})
    except Exception as ex:
        print(ex)
        return jsonify({"mensaje":"error al eliminar el usuario"})
    finally:
        cursor.close()

# ------- Update Delete tabla perfiles    -----------



# ------- Update Delete tabla lenguajes   -----------




def pagina_no_encontrada(error):
    return "<h1>La página no existe</h1>",404

if __name__=='__main__':
    app.config.from_object(config["development"])
    app.register_error_handler(404,pagina_no_encontrada) 
    app.run()
    