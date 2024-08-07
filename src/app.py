from flask import Flask, jsonify, request
from flask_mysqldb import MySQL 

from config import config

app=Flask(__name__)

conexion=MySQL(app)


# faltan todas las validaciones en cada endpoint
# verificar si la peticion existe o no en la bbdd antes de ejecutarla

#los get deberian ir en relacion a lo que queremos mostrar en cada pagina y no en relacion a las tablas?
#no hice get de informacion, perfiles y lenguajes


# ------- usuario nuevo -----------

@app.route('/registrar', methods=["POST"]) 
def registrar():
    datos= request.get_json()
    nombre = datos.get('nombre') 
    apellido = datos.get('apellido')
    email = datos.get('email')
    password = datos.get('password')
    informacion_adicional = datos.get('informacion_adicional')
    image = datos.get('image') #cursor de tiempo para que baje en tiempo real
    
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
        conexion.connection.commit()
        return jsonify({"mensaje": "Usuario registrado"})
        
    except Exception as ex:     # mostrar mensaje segun el tipo de error
        print(f"Error: {ex}") 
        return jsonify({"mensaje": "Error al registrar el usuario"})
    
    finally:
        cursor.close()


# ------- CRUD tabla usuarios -----------

#busca por nombre y apellido si dan los dos datos  o solo por nombre o apellido si dan uno solo
#cambiar a participantes y agregar el resto de la info
@app.route('/usuario', methods=["GET"])
def usuario():
    nombre = request.args.get('nombre')
    apellido = request.args.get('apellido')
    try:
        cursor=conexion.connection.cursor()
        if nombre is not None and apellido is not None:
            sql = "SELECT * FROM usuarios WHERE nombre = %s AND apellido= %s"
            cursor.execute(sql, (nombre,apellido))
            datos=cursor.fetchone()
            if datos is not None:
                usuario = {"id":datos[0], "nombre":datos[1], "apellido":datos[2], "email": datos[3], "contraseña":datos[4]}
                return jsonify({"nombre":usuario,"mensaje": "Datos del usuario"})
            else:
                return jsonify({"mensaje": "Usuario no encontrado"})    
        else:
            sql = "SELECT * FROM usuarios WHERE nombre = %s or apellido= %s"
            cursor.execute(sql, (nombre,apellido))
            datos=cursor.fetchall()
            print(datos)
            if datos:
                usuarios = []
                for user in datos:
                    usuario = {"id":user[0], "nombre":user[1], "apellido":user[2], "email": user[3], "contraseña":user[4]}
                    usuarios.append(usuario)
                return jsonify({"usuarios":usuarios,"mensaje":"Todos los usuarios"})
            else:
                return jsonify({"mensaje": "Usuario no encontrado"})        
    except Exception as ex:    
        return jsonify({"mensaje": "Error al buscar datos del usuario"})    
    finally:
        cursor.close()



@app.route('/usuarios_todos', methods=["GET"]) 
def mostrar_todos_usuarios():
    try:
        cursor=conexion.connection.cursor()
        sql = "SELECT * FROM usuarios"
        cursor.execute(sql)
        datos=cursor.fetchall()
        usuarios = []
        for user in datos:
            usuario = {"id":user[0], "nombre":user[1], "apellido":user[2], "email": user[3], "contraseña":user[4]}
            usuarios.append(usuario)
        return jsonify({"usuarios":usuarios,"mensaje":"Todos los usuarios"})
        
    except Exception as ex:    
        return jsonify({"mensaje": "Error al buscar datos del usuario"})    
    finally:
        cursor.close()



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
        sql = "UPDATE usuarios SET nombre=%s, apellido=%s, email=%s, password=%s WHERE id=%s"
        cursor.execute(sql, (nombre, apellido, email, password, id))
        conexion.connection.commit()
        return jsonify({"mensaje": "Datos actualizados"})        
    except Exception as ex:
        print(f"Error: {ex}") 
        return jsonify({"mensaje": "Error al registrar el usuario"}), 500    
    finally:
        cursor.close()



@app.route('/usuario', methods=["DELETE"])
def borrar_usuario():
    id = request.args.get('id')
    try:
        cursor=conexion.connection.cursor()
        sql = "DELETE FROM usuarios WHERE id=%s"  #join al resto de las tablas del usuario y borrar tambien
        cursor.execute(sql,(id,))
        conexion.connection.commit()
        return jsonify({"mensaje":"Has eliminado el usuario"})
    except Exception as ex:
        print(ex)
        return jsonify({"mensaje":"error al eliminar el usuario"})
    finally:
        cursor.close()
    
    #redireccionar a pagina principal



# ------- CRUD tabla informacion -----------

@app.route('/informacion', methods=["PUT"])
def actualizar_informacion():
    id = request.args.get('id')  # me envia email, busco email en base de datos para traer id y hago peticion con id
    datos= request.get_json()
    informacion = datos.get('informacion_adicional')
    image = datos.get('image')    
    try: 
        cursor=conexion.connection.cursor()
        sql = """UPDATE informacion 
                INNER JOIN usuarios ON informacion.usuario = usuarios.id
                SET informacion.informacion_adicional=%s, 
                informacion.image=%s 
                WHERE usuarios.id=%s"""
        cursor.execute(sql, (informacion, image, id))
        conexion.connection.commit()
        return jsonify({"mensaje": "Datos actualizados"})        
    except Exception as ex:
        print(f"Error: {ex}") 
        return jsonify({"mensaje": "Error al registrar el usuario"}), 500    
    finally:
        cursor.close()

# ------- CRUD tabla perfiles    -----------


# ------- CRUD tabla lenguajes   -----------




def pagina_no_encontrada(error):
    return "<h1>La página no existe</h1>",404


if __name__=='__main__':
    app.config.from_object(config["development"])
    app.register_error_handler(404,pagina_no_encontrada) 
    app.run()
    