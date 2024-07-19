from flask import Flask, jsonify, request
from flask_mysqldb import MySQL 

from config import config

app=Flask(__name__)

conexion=MySQL(app)


@app.route('/usuario', methods=["GET"])
def datos_usuario():
    nombre = request.args.get('nombre')
    apellido = request.args.get('apellido')
    try:
        cursor=conexion.connection.cursor()
        sql = "SELECT * FROM usuarios WHERE nombre = %s AND apellido = %s"
        cursor.execute(sql, (nombre, apellido))
        datos=cursor.fetchone()
        print(datos)
        if datos != None:
            usuario = {"nombre":datos[1], "apellido":datos[2], "email": datos[3], "contraseña":datos[4]}
            return jsonify({"usuarios":usuario,"mensaje": "Datos del usuario"})
        else:
            return jsonify({"mensaje": "Usuario no encontrado"})
    
    except Exception as ex:
        return jsonify({"mensaje": "Error al buscar datos del usuario"})

   
def pagina_no_encontrada(error):
    return "<h1>La página no existe</h1>",404


if __name__=='__main__':
    app.config.from_object(config["development"])
    app.register_error_handler(404,pagina_no_encontrada) 
    app.run()
    